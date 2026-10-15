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

## What a judge sees in the workspace

| Name in the workspace | Block | What it does |
|---|---|---|
| **Intake clerk** | agent, model `own/Qwen3.8-27B` (AMD Token Factory, under "Your models") | Writes the review task for a routed form: which field to check and why. Never guesses a value. |
| **Tally sheet reader** | agent marked as data extractor | Independent third reader of the masked page (schema "Tally sheet type 2", 23 fields). |
| **Review hand-off** | workflow, 4 steps, on | AgentCall (Intake clerk) → AI Tool `translate` → Script (assemble) → Output. Optional Email step to a reviewer. |
| **Record filing** | workflow, 3 steps, on | Script: the form's 4 identities, generated from our schema, re-checked in Evolus with zero AI → CreateFile → Output. |
| **Records register** | knowledge library | Accepted records, one document per form (needs a User API key to create, see below). |

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
```

Ids go to `evolus/ids.json`. It holds no secrets and is safe to commit; the config reads it before the environment.
Keys come only from the environment or an untracked `.env`: `EVOLUS_KEY`, `EVOLUS_APP_ID`, and optionally
`EVOLUS_USER_KEY` and `EVOLUS_REVIEWER_EMAIL` (adds an Email hand-off step).

**For the extractor and the library:** create a personal User API key (Evolus API reference page, "API Keys" tab),
put it in `.env` as `EVOLUS_USER_KEY`, and run `python -m evolus setup` again. Without it, setup creates everything
else and lists these two as not created.

## AMD calls

Our limiter (6 req/min) cannot see calls that Evolus makes from its servers. Per routed form there is 1 AgentCall
(Evolus retries a failing call up to 3 times); an accepted form makes none (the filing Script is not AI). The
extractor adds 1 per form once configured. The run above made 3 Token Factory calls through Evolus. During
development we made 2 more: 1 direct function-calling probe of Gemma and 1 trial hand-off.

## Privacy and framing

Only masked pages (`data/masked/**`) are sent, and a form without one is refused. Vote rows are `OPT01`…`OPT15`
("Option 01"…). Notes pass through the app's neutralizer, and nothing is totalled by option. Keys are never printed.
Every log line, record and `ids.json` passes through `redact()` (`tests/test_evolus_flow.py`,
`tests/test_evolus_setup.py`).
