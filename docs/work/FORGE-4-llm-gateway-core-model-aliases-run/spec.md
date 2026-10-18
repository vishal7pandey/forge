# FORGE-4 — LLM gateway core: model aliases, run context, usage ledger, per-run budget

Status: draft · Risk: medium · Jira: FORGE-4
Created: 2026-10-18 · Slug: llm-gateway-core-model-aliases-run

## Problem

Forge agents will make many model calls per run. If each component calls a provider SDK directly, nobody can say what a
run cost, a looping agent can spend without limit until the invoice arrives, and swapping a model means editing every
caller. The charter's C1 and C6 (cost per resolved task) cannot be measured at all without one place every call passes
through. Today Forge has no model-calling code.

## Users and context

- **Forge components** (the harness in FORGE-5, the benchmark runner in FORGE-7) that need a model response.
- **The owner**, reading what a run or benchmark cost.
- Design grounding: design repo `02-llm-gateway.md` (client contract, aliases, run context), `03-prompt-finops.md` (ledger
  fields, price catalogue, reservations), ADR-003 (own the gateway front, LiteLLM for provider translation). This item is
  the vertical-slice subset those documents name. There is no existing code in `src/forge/` beyond the template.

## Goals and non-goals

**Goals**
- One API for chat completions with tool calling, addressed by alias.
- Hard per-run budget enforced before a call is sent.
- A durable usage ledger, one row per call, priced from a versioned price catalogue.
- Fully testable offline.

**Non-goals**
- An HTTP endpoint. The sandboxed agent in FORGE-5 will need one; that item adds it on top of this API.
- Streaming responses, embeddings, structured-output enforcement, prompt caching controls, batch.
- Team or tenant budgets, chargeback, FOCUS export (design 03, Phase 1).
- Guardrails and policy (PDP) checks on calls (FORGE-6 and later).
- Automatic fallback to another alias or provider on errors; retries beyond what the provider library does.
- Content storage of prompts and completions (only hashes are recorded here).

## Requirements

- R1. The system must expose one call that takes a model alias, a list of messages, optional tool definitions, an optional
  `max_output_tokens`, and a run context, and returns the response text, any tool calls, and the token usage.
- R2. The system must resolve an alias to a provider model through configuration; an unknown alias must be rejected before
  any provider is contacted.
- R3. The run context must carry `tenant`, `team`, `run_id` and `step`; a call with any of these missing or empty must be
  rejected before any provider is contacted.
- R4. Each run must have a budget in US dollars, set when the run is opened. Before sending a call, the system must reserve
  the call's worst-case cost (input tokens counted locally, plus `max_output_tokens`, at catalogue prices) and must refuse
  the call when the reservation would exceed the run's remaining budget.
- R5. After a call, the system must replace the reservation with the actual cost computed from the reported token usage, so
  the remaining budget reflects actual spend.
- R6. The system must append one usage row per call attempt, successful or failed, with: time, tenant, team, run_id, step,
  alias, provider, provider model, input tokens, output tokens, cost in USD, price-catalogue version, latency in ms,
  outcome (`ok`, `provider_error`, `budget_refused`, `invalid_request`), and a SHA-256 hash of the request messages.
- R7. Usage rows must survive a process restart and be queryable by run_id, with totals of cost and tokens per run.
- R8. Prices must come from a catalogue file that carries a version; a cost is always computed with, and recorded against,
  one catalogue version. An alias whose provider model has no price must be rejected at configuration load.
- R9. The system must work with a deterministic fake provider (configured responses and token counts) so that every
  requirement above can be tested without network access or API keys.
- R10. The system must support at least one real provider path through LiteLLM, using credentials from environment
  variables only.
- R11. A provider error must be returned to the caller as a typed gateway error, release the call's reservation, and be
  recorded (R6) with outcome `provider_error`.

## Acceptance criteria

- AC1. (R1, R9) Given alias `coding.fast` mapped to the fake provider, which is configured to answer "hello" with 12 input and
  3 output tokens, a call with a valid run context returns text "hello", no tool calls and usage `{input: 12, output: 3}`.
- AC2. (R1) Given the fake provider configured to return a tool call `read_file(path="a.py")`, the call result contains
  exactly that tool call with its arguments as a mapping.
- AC3. (R2) A call with alias `does.not.exist` fails with an "unknown alias" error, the fake provider records zero calls, and
  one usage row with outcome `invalid_request` is written.
- AC4. (R3) A call whose run context has an empty `run_id` fails with a "run context" error naming the missing field, and the
  fake provider records zero calls.
- AC5. (R4) Given a run opened with a 0.010 USD budget and prices making a call's worst-case reservation 0.012 USD, the call
  fails with a budget error, the fake provider records zero calls, and a usage row with outcome `budget_refused` and cost 0
  is written.
- AC6. (R4, R5) Given a run with a 1.00 USD budget and three successful calls costing 0.10 USD each by actual usage, the
  remaining budget is 0.70 USD, and a fourth call whose reservation is 0.75 USD is refused.
- AC7. (R6) After AC1, the ledger holds exactly one row whose fields match R6, with outcome `ok`, the catalogue version from
  the price file, and a request hash equal to the SHA-256 of the canonical JSON of the messages.
- AC8. (R7) Rows written by one process are returned by a run_id query from a new process, and the per-run totals equal
  the sum of the rows.
- AC9. (R8) Loading a configuration where an alias points at a model missing from the price catalogue fails with an error
  naming the alias and the model; no call is possible with that configuration.
- AC10. (R11) Given the fake provider configured to raise an error, the caller gets a gateway provider error, the run's
  remaining budget is unchanged, and a row with outcome `provider_error` is written.
- AC11. (R10) With a provider key set in the environment, a call with alias `coding.fast` mapped to a real model through
  LiteLLM returns non-empty text and a usage row with non-zero tokens. This test is marked and skipped when no key is set;
  it is run once by hand and its result recorded in the test plan.
- AC12. (R4) Two concurrent calls on the same run whose reservations together exceed the remaining budget result in at most
  one being sent to the provider.

## Edge cases and failure modes

- Empty message list: rejected as `invalid_request` before any provider call.
- `max_output_tokens` absent: the alias's configured default is used for the reservation; an alias without a default makes
  the call `invalid_request`.
- Provider reports usage higher than reserved: the actual cost is recorded even if it pushes the run over budget; the next
  call is refused. Overshoot is bounded by one call, and the row shows it.
- Provider returns no usage: the call is recorded with the reserved (worst-case) cost and a flag in the row, so spend is
  never under-counted.
- Run not opened: a call naming an unknown `run_id` is rejected as `invalid_request`.
- Ledger write fails: the call result is still returned, and the failure is raised as an error after it, so a lost row is
  never silent.
- Price catalogue changes between calls: each row records the version it was priced with.

## Non-functional requirements

- Security (`.factory/policies/security.md`): provider keys only from environment variables, never logged, never written to
  the ledger; prompts and completions are not stored, only their hash.
- Overhead: the gateway adds at most 5 ms (p95) to a fake-provider call on the developer machine, excluding the provider.
- Offline: the full test suite passes with no network and no keys (AC11 skipped).

## Assumptions

- Budget is per run only for this item; team and tenant budgets come later (design 03).
- Token counting before a call may be approximate (a tokenizer or a conservative character-based estimate), as long as it
  is not lower than the provider's count by more than 10% in tests; the actual cost always replaces it (R5).
- The first real provider is Anthropic via LiteLLM; others are configuration only.
- In-process API only (see non-goals); the stack follows D-002 (one Python package) unless the owner decides otherwise.

## Risks and dependencies

- Risk is **medium**: it controls spend (money) but only for the owner's own experiments, it is internal and easily
  reversible, and no customer data or auth is involved. Raise to high if it ever meters someone else's spend.
- Depends on D-002 (stack) for the plan; the spec itself is stack-neutral.
- LiteLLM is a fast-moving dependency (design 18): pinned, behind a provider interface, so it can be replaced per provider.
- Pre-call token estimates that are too low would let one call overshoot; bounded by the edge-case rule above.
