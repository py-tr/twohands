# Two Hands on Evolus: paper-form intake for a records office

**User:** the records-office clerk who today double-keys every paper form. **Process:** a scanned form arrives; it is
read, checked and either filed as a record or handed to a person with the failing field named. **Gain:** forms whose
own arithmetic holds are filed with no keying (49% on our difficult pilot, 0 of 462 accepted fields wrong). The rest
reach the clerk with the field, its crop and a task written in English and Spanish.

Evolus is where the case lives. Our code (`evolus/`) builds the workspace and drives it over the Evolus REST API
(spec: [`docs/evolus-openapi.json`](evolus-openapi.json), OpenAPI 3.0.4). The decision stays with the paper's
arithmetic, never with a model.

```
masked page ──► primary read (Gemma-4-31B-IT on AMD, measured) ──► our gate ─┐
           └──► Evolus extractor "Tally sheet reader" (independent) ──► gate ─┤ compare
                                                                               ▼
  accepted ──► workflow "Record filing": Script re-checks the paper's identities in Evolus (no AI)
               ──► CreateFile (JSON record) ──► Output                 [+ library "Records register"]
  routed   ──► workflow "Review hand-off": AgentCall "Intake clerk" (open model on AMD Token Factory)
               ──► AI Tool translate (Spanish) ──► Script (assemble the task) ──► [Email] ──► Output
               ──► the task lands on the Two Hands review desk (notes EN/ES, crop link, run status)
```

## The audit process in Evolus ("Audit your capture")

The buyer is a capture auditor. Two Hands compares a keyed CSV with the paper and orders every disputed field by its
evidence (`app/capture_audit.py`). On the audit report, **Open as Evolus cases** sends each strong-evidence field
(18 on the sample of 300 forms) to the workflow **Audit finding**, one run per field (`evolus/audit.py`). Each case
comes back to the report next to its photo, and the auditor's **Confirm** / **Not an error** is written back.

```
audit report ──► "Open as Evolus cases" (strong tier, at most 18, shared limiter, 2 in flight)
   one field = form id, field (Option NN or plain name), keyed value, model digits + words,
               the identities it breaks / the model's value satisfies (with their sums), crop URL, tier
   ──► workflow "Audit finding":
         AgentCall "Intake clerk" ── three-sentence finding, ends "for the auditor to confirm"   (1 AMD call)
         Script (no AI) ─────────── recomputes the evidence score from the inputs (= our rule, 0 AI calls)
         Script (no AI) ─────────── the audit case: finding + score + crop link, status "open"
         [Webhook back to /api/evolus/callback, only when the app has a public URL]
         Output ─────────────────── our app polls the execution and files the case
   ──► report: run id, run status, the drafted finding beside the crop
   ──► Confirm / Not an error ──► case status (open / confirmed / not an error)
                                  ──► Evolus workflow audit of that run (PUT clientData)
                                  ──► [library "Records register": the confirmed finding, once it exists]
```

| Building block (in use) | Type | What it does in the audit |
|---|---|---|
| **Intake clerk** | agent, `own/Qwen3.8-27B` on the AMD Token Factory | Drafts the auditor's finding: what the paper shows, what was keyed, which identity supports the paper. It never decides; every finding ends "for the auditor to confirm". |
| **Audit finding** | workflow: AgentCall, Script, Script, [Webhook], Output | One run per disputed field; the case lands back in Two Hands with status `open`. |
| Script "Recompute the evidence score" | workflow step, no AI | Our evidence rule in JavaScript, run on the raw sums we send: the model cannot change the score. Checked against our Python rule on all 267 disputes (`tests/test_evolus_audit.py`). |
| Workflow audits | `GET/PUT /api/v1/workflow-audits` | Evolus records each run; the auditor's status is written to it as `clientData`. |
| **Review hand-off** | workflow: AgentCall, AI Tool `translate`, Script, Output | The intake side: a routed form goes to the review desk with its task in English and Spanish. |
| AI Tool `translate` | platform AI Tool | The Spanish version of the review task. |
| **Record filing** | workflow: Script (no AI), CreateFile, Output | The intake side: an accepted form's identities are re-checked in Evolus and filed as a JSON record. |
| **Tally sheet reader** + schema "Tally sheet type 2" | data extractor | Once `EVOLUS_USER_KEY` is set: an independent third read of a form, compared field by field. |
| **Records register** | knowledge library | Once `EVOLUS_USER_KEY` is set: accepted records, and each finding the auditor confirms, filed as documents the clerk can answer from. |

The last two need a personal User API key. They **activate by themselves**: the next `python -m evolus run`,
`python -m evolus audit` or "Open as Evolus cases" after `EVOLUS_USER_KEY` appears in the environment or `.env` runs
the idempotent setup, builds both and uses them (`evolus.setup.ensure_user_blocks`). Without the key nothing is faked:
they are listed as not created.

### The real run (2026-10-15, `results/evolus_audit_runs.jsonl`)

`python -m evolus audit` on the sample audit (the official first capture of the 300 pre-registered forms): 267
disputed fields, 18 with strong evidence. All **18 were sent and all 18 came back** as audit cases with a drafted
finding, status `open`. In all 18 the evidence score recomputed by the Evolus Script equals ours (`agrees_with_app`).
Example (form 050815B0100, Option 07):

> *The paper shows 175 in digits and one hundred seventy-five in words. The keyed value for Option 07 is 75. The
> paper's identity rows sum to TOTAL supports the paper's value, and the keyed value breaks rows sum to TOTAL, for the
> auditor to confirm.*

AMD calls: 18 (one AgentCall per case, each started on a token of the shared limiter, at most 2 in flight). The
clerk ran on Qwen3.8-27B: on 2026-10-15 Gemma-4-31B-IT was not on the Token Factory's model list (one probe: HTTP 400
"not supported"). The AgentCall took 96 s at the median and up to 31 min on a busy shared endpoint. A case still
running after 6 min is recorded as `timeout` and the next field starts; the next call collects it without sending it
again (one case did this, then completed). Evolus kept a workflow audit for each run, which is where the auditor's
status goes.

## What a judge sees in the workspace

| Name in the workspace | Block | What it does |
|---|---|---|
| **Intake clerk** | agent, model `own/Qwen3.8-27B` (AMD Token Factory, under "Your models") | Writes the review task for a routed form: which field to check and why. Never guesses a value. |
| **Tally sheet reader** | agent marked as data extractor | Independent third reader of the masked page (schema "Tally sheet type 2", 23 fields). |
| **Review hand-off** | workflow, 4 steps, on | AgentCall (Intake clerk) → AI Tool `translate` → Script (assemble) → Output. Optional Email step to a reviewer. |
| **Record filing** | workflow, 3 steps, on | Script: the form's 4 identities, generated from our schema, re-checked in Evolus with zero AI → CreateFile → Output. |
| **Records register** | knowledge library | Accepted records, one document per form (needs a User API key to create, see below). |
| **Audit finding** | workflow, 4 steps, on | AgentCall (Intake clerk drafts the finding) → Script (evidence score, no AI) → Script (the audit case) → Output; a Webhook step back to Two Hands is added when the app has a public URL. |

The tags on every block are `two-hands` and `paper-form-intake`.

## The real run (2026-10-15, `results/evolus_runs.jsonl`)

`python -m evolus run --pick 2,3` ran on 5 masked forms. The model was Qwen3.8-27B: Gemma-4-31B-IT was down on the
Token Factory (provider 503).

| Form | Decision | Evolus run | Steps (ms) |
|---|---|---|---|
| 010441C0100 | accepted | Record filing `338e6f6a…` Completed, 4/4 identities hold, filed | Script 1, CreateFile, Output |
| 010452B0100 | accepted | Record filing `c672ff73…` Completed, filed | Script 1, CreateFile, Output |
| 010445C0100 | routed (3 fields) | Review hand-off `cb72ff73…` Completed | Intake clerk 47,768; translate 2,780; Script; Output |
| 080305B0100 | routed (section 5 ≠ section 7) | Review hand-off `f61d4b9b…` Completed | Intake clerk 20,940; translate 1,465; Script; Output |
| 010469C0400 | routed (6 fields unreadable) | Review hand-off `bdd761a7…` Completed | Intake clerk 24,333; translate 1,756; Script; Output |

The Spanish notes are real AI Tool output, for example: *"Verifica los valores en papel de «Votantes +
representantes» y «Papeletas extraídas de las urnas». El formulario se derivó porque esas secciones no coinciden…"*.
In this run the extractor and the library were **skipped**, not simulated: creating them needs a User API key (below).

## Endpoints used

Base `https://api.evolus.ai`. Auth: REST `X-ApiKey` + `X-Application-Id` (application key); the operations marked
**U** need a personal `X-User-ApiKey` according to the spec. Agent chat uses `Authorization: Bearer`. Sources: the
spec in this folder, and https://evolus.ai/developers (public summary).

| Endpoint | Used by | Note |
|---|---|---|
| `GET/POST /api/v1/agents`, `PUT /api/v1/agents/{agentId}` | setup | find or create the agents and set `modelKey` (`own/<alias>`) |
| `GET/POST/PUT /api/v1/agents/{agentId}/json[/{id}]` | setup | extractor schema "Tally sheet type 2" (**U**) |
| `POST /api/v1/agents/{agentId}/json/{id}/ask-file?useWebhook=false` | run | extract the masked page |
| `GET /api/v1/memories`, `POST /api/v1/memories/simple`, `POST /api/v1/agents/{agentId}/memories` | setup | library (**U**) |
| `POST /api/v1/memories/{memoryId}/documents` | run | file an accepted record |
| `GET /api/v1/workflows/step-catalog[/{key}]` | development | block docs: step types, placeholders, own models |
| `GET/POST /api/v1/workflows`, `GET/PUT/DELETE /api/v1/workflows/{id}`, `POST /api/v1/workflows/{id}/steps` | setup | build both workflows and switch them on (`isActive`) |
| `POST /api/v1/workflows/{id}/execute` (multipart: `input`, `parameters`, optional `callbackUrl`…) | run | execution id from the `X-Workflow-Execution-Id` header |
| `GET /api/v1/workflows/{id}/executions/{executionId}` | run | `status`, `output`, `stepStates` |
| `GET /api/v1/workflow-audits?workflowId=`, `PUT /api/v1/workflow-audits/{auditId}` | audit | write the auditor's status (`clientData`) to the run's workflow audit |
| `GET /api/v1/ai-tools`, `POST /api/v1/ai-tools/translate/run` | check, fallback | `translate` takes `target` (free text: `"Spanish"`; `"es"` gave Italian) |
| `GET /v1/models`, `POST /v1/chat/completions` | check, fallback | OpenAI-compatible agent chat, model `{applicationId}:{agentId}` |

Our side: `POST /api/gate` (Bearer `TWOHANDS_GATE_TOKEN`), `GET /api/evolus/case/{form}`, `POST /api/evolus/callback`
(header `X-Callback-Key`).

## Setup

The one manual step is **connecting the model**, done once in the Evolus UI under "Your models": an
OpenAI-compatible server with the AMD Token Factory base URL and key, models `Gemma-4-31B-IT` and `Qwen3.8-27B`.
Everything else is one command:

```bash
python -m evolus setup                          # find or create agents, extractor, library, workflows; switch on
python -m evolus setup --model Gemma-4-31B-IT   # move both agents to Gemma (one command, idempotent)
python -m evolus check                          # which blocks are configured; agents; AI Tools
python -m evolus run --pick 2,3                 # 2 accepted + 3 routed forms -> results/evolus_runs.jsonl
python -m evolus audit --max 18                 # the sample audit's strong fields -> results/evolus_audit_runs.jsonl
```

Ids go to `evolus/ids.json`. It holds no secrets and is safe to commit; the config reads it before the environment.
Keys come only from the environment or an untracked `.env`: `EVOLUS_KEY`, `EVOLUS_APP_ID`, and optionally
`EVOLUS_USER_KEY` and `EVOLUS_REVIEWER_EMAIL` (adds an Email hand-off step).

**For the extractor and the library:** create a personal User API key (Evolus API reference page, "API Keys" tab),
put it in `.env` as `EVOLUS_USER_KEY`, and run `python -m evolus setup` again. Without it, setup creates everything
else and lists these two as not created.

## AMD calls

Our limiter (6 req/min) cannot see calls that Evolus makes from its servers, so the audit runner takes one token
from the shared limiter (`cache/ratelimit.json`, also used by the batch) before each run it starts, keeps at most 2
runs in flight and sends at most 18 per click. Each audit case is exactly 1 AMD call (Evolus retries a failing AgentCall up to 3 times). Per routed form there is 1 AgentCall
(Evolus retries a failing call up to 3 times); an accepted form makes none (the filing Script is not AI). The
extractor adds 1 per form once configured. The run above made 3 Token Factory calls through Evolus. During
development we made 2 more: 1 direct function-calling probe of Gemma and 1 trial hand-off.

## Privacy and framing

Only masked pages (`data/masked/**`) are sent, and a form without one is refused. Vote rows are `OPT01`…`OPT15`
("Option 01"…). Notes pass through the app's neutralizer, and nothing is totalled by option. Keys are never printed.
Every log line, record and `ids.json` passes through `redact()` (`tests/test_evolus_flow.py`,
`tests/test_evolus_setup.py`).
