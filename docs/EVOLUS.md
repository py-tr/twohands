# Two Hands on Evolus: paper-form intake for a records office

**User:** the records-office clerk who today double-keys every paper form. **Process:** a scanned form arrives; it is
read, checked and either filed as a record or handed to a person with the failing field named. **Gain:** forms whose
own arithmetic holds are filed with no keying (18% of a pre-registered random 300 with one reader, 2 wrong of 1,210
accepted fields; 30% with two readers, 0 wrong of 1,958, a secondary tier with a lighter gate, judged against the
official capture). The rest
reach the clerk with the field, its crop and a task written in English and Spanish.

**Evolus event workspace: py_tr (event code AMDACT3).** Source: the Evolus API, `GET /api/v1/agents/{agentId}` ->
`application.name` = `py_tr` (application `798f7408-...`, created 2026-10-15 through the event join link), cached in
`evolus/ids.json` by `python -m evolus setup` and shown in the Evolus section of the site (`/results#evolus`), in the
README and on the "What ran on AMD" slide. Evolus asked that the name be shown clearly and that the workspace and
the model endpoint stay online until **Nov 15, 2026** for their review (Evolus on the lablab Discord, 2026-10-16, and
the Evolus CTO at the kickoff; quoted in [sources/event-rules.md](sources/event-rules.md)); we keep both up until then.

## Requirement 2: the main agent's model

**Confirmed by the Evolus team (Discord, 2026-10-16, LazyLoad):** "Token Factory works fine on Evolus and does count for the Track."


The Evolus agent's model is Gemma-4-31B-IT on the AMD Token Factory, connected under 'Your models' as an
OpenAI-compatible server; the event page's Evolus section allows 'an open model through a vLLM endpoint on AMD
Developer Cloud, or any OpenAI-compatible provider'; AMD stated that the Token Factory API key is all a team needs
for ACT III.

Sources, quoted in [sources/event-rules.md](sources/event-rules.md): the event page's Evolus block, "Bring your own model. Event workspaces run
their agents on the model each team connects: an open model through a vLLM endpoint on AMD Developer Cloud, or any
OpenAI-compatible provider" (page refresh of 2026-10-13; the Requirements line on the same page still says
"through your own vLLM endpoint on AMD Developer Cloud"); and AMD (Maharshi, AMD admin, lablab Discord, 2026-10-15 ~18:11 UTC):
"for hackathon no cloud credits needed only apikey from notebooks.amd.com/tokenfactory". Evolus then confirmed it (above).

Both agents ("Intake clerk", "Tally sheet reader") were moved from Qwen3.8-27B to Gemma-4-31B-IT on 2026-10-16
(`python -m evolus setup --model Gemma-4-31B-IT`), after Gemma answered a probe on the Token Factory and then a chat
through the Evolus agent itself (`POST /v1/chat/completions`, model `{applicationId}:{agentId}`, reply "ready"). The
agent reads back `modelKey own/gemma-4-31b-it`, `modelState ok`. The runs dated 2026-10-15 in `results/evolus_runs.jsonl`
and `results/evolus_audit_runs.jsonl` were made on Qwen3.8-27B while Gemma was unavailable on the Token Factory
(2026-10-15 15:41 to 2026-10-16 02:06 UTC, `results/endpoint_health.jsonl`); runs since the move (2026-10-16) use
Gemma-4-31B-IT. If a self-hosted vLLM is ever connected, it is listed
here as a second model under "Your models"; none is connected today.

Evolus is where the case lives. Our code (`evolus/`) builds the workspace and drives it over the Evolus REST API
(spec: [`docs/evolus-openapi.json`](evolus-openapi.json), OpenAPI 3.0.4). The decision stays with the paper's
arithmetic, never with a model.

```
masked page ──► primary read (Gemma-4-31B-IT on AMD, measured) ──► our gate ─┐
           └──► Evolus extractor "Tally sheet reader" (independent) ──► gate ─┤ compare
                                                                               ▼
  accepted ──► workflow "Record filing": Script re-checks the paper's identities in Evolus (no AI)
               ──► CreateFile (JSON record) ──► Output                 [+ library "Records register"]
  routed   ──► workflow "Review hand-off": AgentCall "Intake clerk" (Gemma-4-31B-IT on AMD Token Factory)
               ──► AI Tool translate (Spanish) ──► Script (assemble the task) ──► [Email] ──► Output
               ──► the task lands on the Two Hands review desk (notes EN/ES, crop link, run status)
```

## In the critical path: the live audit

The live worker (`twohands/worker.py`, the standing audit of presidential tally sheets) calls Evolus for every form
it commits (`evolus/live.py`, `LiveHook`). Each **strong-evidence dispute** (the model's read differs from the
official capture; evidence score >= 6 under the audit's rule, `app/capture_audit.evidence`; not on a form whose
row-label check failed; not on a form where the certified count shows the model misread) starts one run of the
workflow **"Audit finding"**, with the same input as an audit case (`case_id` `live-<form>-<Option NN>`). Not every
routed form goes to Evolus: each run is one call on the shared AMD key, so

- runs are capped at **60 per UTC day** (`EVOLUS_DAILY_RUNS`, counted in `cache/evolus_daily.json`; the review
  desk's sends count too); over the cap a dispute is logged as not sent, never queued for later;
- each start takes a token from the shared rate limiter (`cache/ratelimit.json`), like every other AMD call;
- sending and polling run on the hook's own thread; an Evolus error is recorded on the case and never stops the audit.

The case comes back as designed for audit cases: our side polls the execution (or a Webhook callback delivers it,
merged by execution id), and the finding, the recomputed score and the run status are stored in
`live_audit/evolus_cases.json`. The site shows today's count and the latest cases in its Evolus section
(`/results#evolus`; JSON at `GET /api/evolus/live`). `EVOLUS_LIVE=0` turns the hook off; without `EVOLUS_KEY`,
`EVOLUS_APP_ID` and the workflow id it is off by itself. The running worker picks the hook up at its next start.
Tests: `tests/test_evolus_live.py` (Evolus mocked).

**Review desk.** Each routed form on `/review` without an Evolus case has **Send to Evolus**
(`POST /api/evolus/send/{form}`): it runs the intake case for that form in the background (workflow "Review
hand-off": the Intake clerk drafts the task, AI Tool translate, Script), within the same daily cap; the run then
shows on the card.

## Routed cases in the workspace (`python -m evolus routed`, results/evolus/executions.jsonl)

**Evolus workspace py_tr: 150 "Audit finding" executions of real routed fields (100 from the 300 run, 50 from Colima), 150 completed with a drafted finding (100%), 0 failed, 0 still open; model reported by Evolus: own/gemma-4-31b-it (ok). Source: results/evolus/executions.jsonl.** Window 2026-10-17T00:53 to 2026-10-17T01:56 UTC; in all 150 the evidence score recomputed by the Evolus Script equals ours; 0 HTTP errors.

Each execution is one run of the workflow **"Audit finding"** on one real case: a field the gate refused in a
real read of a masked form (digits that disagree with the words, the field on the right of an identity that does not
hold, a box not read, or a row label out of place), with the link to its masked crop (`/crop/<form>/<code>.jpg`, the
app's crop pipeline on `data/masked/**`; the sha256 of the crop bytes is in the ledger) and the task for the clerk
("Look at <field> on the paper ... and key the value the paper shows. The form was routed because ..."). The Intake
clerk drafts the finding, the Evolus Script recomputes the evidence score with no AI. Sources: the pre-registered
random 300 (`results/calls_gemma.jsonl`; "keyed" is that form's official first capture, as in the sample audit) and
the Colima complete-state read (`results/colima/calls_gemma.jsonl`, Amendment 8b; nothing keyed is attached, and
nothing is compared with the official count here). One case per routed form, forms in the order of
sha256(case id), fields already sent as audit cases skipped. Only Option NN and plain field names leave the app; a
guard refuses any input with a party name, a schema row id or an image path. Pacing: one start every 25 s, at most 4
runs open, a shared-limiter token per start (one AMD call each); Evolus allows 60 requests/min per application
(docs/evolus-openapi.json, "Rate limits"). The ledger makes it idempotent: a case id with an execution id is never
sent again, and an open run is polled, not re-sent. Generated and checked by `python scripts/evolus_ledger.py
[--check]` (`make eval`); the table of every execution is in `results/evolus/summary.md`.

## The audit process in Evolus ("Audit your capture")

The buyer is the state institute (OPLE) that runs the regulated second capture; the capture auditor who works for it is the user here. Two Hands compares a keyed CSV with the paper and orders every disputed field by its
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
| **Intake clerk** | agent, `own/Gemma-4-31B-IT` on the AMD Token Factory (Qwen3.8-27B until 2026-10-16) | Drafts the auditor's finding: what the paper shows, what was keyed, which identity supports the paper. It never decides; every finding ends "for the auditor to confirm". |
| **Audit finding** | workflow: AgentCall, Script, Script, [Webhook], Output | One run per disputed field; the case lands back in Two Hands with status `open`. |
| Script "Recompute the evidence score" | workflow step, no AI | Our evidence rule in JavaScript, run on the raw sums we send: the model cannot change the score. Checked against our Python rule on all 267 disputes (`tests/test_evolus_audit.py`). |
| Workflow audits | `GET/PUT /api/v1/workflow-audits` | Evolus records each run; the auditor's status is written to it as `clientData`. |
| **Review hand-off** | workflow: AgentCall, AI Tool `translate`, Script, Output | The intake side: a routed form goes to the review desk with its task in English and Spanish. |
| AI Tool `translate` | platform AI Tool | The Spanish version of the review task. |
| **Record filing** | workflow: Script (no AI), CreateFile, Output | The intake side: an accepted form's identities are re-checked in Evolus and filed as a JSON record. |
| **Tally sheet reader** + schema "Tally sheet type 2" | data extractor | Once `EVOLUS_USER_KEY` is set: an independent third read of a form, compared field by field. |
| **Records register** | knowledge library | Once `EVOLUS_USER_KEY` is set: accepted records, and each finding the auditor confirms, filed as documents the clerk can answer from. |

The last two need a personal User API key. **Checked 2026-10-16:** the workspace key in `EVOLUS_KEY`, sent as
`X-User-ApiKey` (+ `X-Application-Id`) on `GET /api/v1/agents/{agentId}/json` and `GET /api/v1/memories`, is refused
with HTTP 401 `auth.invalid_user_api_key`: one key does **not** work as both. `EVOLUS_USER_KEY` is not set, so the
extractor schema and the library are not created yet; everything else is ready. They **activate by themselves**: the next `python -m evolus run`,
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
| **Intake clerk** | agent, model `own/Gemma-4-31B-IT` (AMD Token Factory, under "Your models"; Qwen3.8-27B until 2026-10-16) | Writes the review task for a routed form: which field to check and why. Never guesses a value. |
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
`python -m evolus setup` keeps the agents' current model unless `--model` is given, and records the workspace name.
Everything else is one command:

```bash
python -m evolus setup                          # find or create agents, extractor, library, workflows; switch on
python -m evolus setup --model Gemma-4-31B-IT   # move both agents to Gemma (done 2026-10-16; idempotent)
python -m evolus check                          # which blocks are configured; agents; AI Tools
python -m evolus run --pick 2,3                 # 2 accepted + 3 routed forms -> results/evolus_runs.jsonl
python -m evolus audit --max 18                 # the sample audit's strong fields -> results/evolus_audit_runs.jsonl
python -m evolus routed --plan r300:100,colima:50  # routed fields as "Audit finding" cases -> results/evolus/executions.jsonl
```

Ids go to `evolus/ids.json`. It holds no secrets and is safe to commit; the config reads it before the environment.
Keys come only from the environment or an untracked `.env`: `EVOLUS_KEY`, `EVOLUS_APP_ID`, and optionally
`EVOLUS_USER_KEY` and `EVOLUS_REVIEWER_EMAIL` (adds an Email hand-off step).

**For the extractor and the library:** create a personal User API key (Evolus API reference page, "API Keys" tab),
put it in `.env` as `EVOLUS_USER_KEY`, and run `python -m evolus setup` again. Without it, setup creates everything
else and lists these two as not created.

## MCP server as an Evolus block (when the app is public)

Evolus (lablab Discord, 2026-10-16, [sources/event-rules.md](sources/event-rules.md)): a custom MCP server can be added by hand from the workspace's
**Connectors** page. Evolus connects from its cloud, so it needs a public HTTPS URL; it is not registered yet.
Steps, once the app has a host:

1. Run the server behind HTTPS: `twohands mcp --http --host 127.0.0.1 --port 8765 --public-host <host>`, with a
   reverse proxy (Caddy, or `cloudflared tunnel --url http://127.0.0.1:8765`) forwarding `https://<host>/mcp`. Model
   reads stay off over HTTP (no `--allow-reads`): the tools gate values, audit stored reads and verify receipts.
2. Check from outside: an MCP client lists `read_form`, `gate`, `audit_capture`, `verify_receipt` at `https://<host>/mcp`.
3. In the workspace **py_tr** -> **Connectors** -> add a custom MCP server: name `Two Hands`, transport
   **Streamable HTTP**, URL **`https://<host>/mcp`**, authentication **none** (the server holds no key; every tool is
   read-only and refuses model calls). If the proxy is set to require a bearer token, enter it as the connector's
   `Authorization: Bearer <token>` header instead; never commit it.
4. Copy the connector's id and attach it to the Intake clerk:
   `python -m evolus mcp-register --url https://<host>/mcp --server-id <id> --apply`
   (`POST /api/v1/agents/{agentId}/mcpserver/{mcpServerId}`, then reads the agent back to show it in `mcpServers`).
5. Ask the clerk in the workspace chat: "gate these values: ...".

## AMD calls

The live worker's Evolus runs: at most 60 a day (`EVOLUS_DAILY_RUNS`), one AMD call each, each paced by the shared
limiter. Our limiter (6 req/min) cannot see calls that Evolus makes from its servers, so the audit runner takes one token
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
