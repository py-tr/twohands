# Two Hands on Evolus: paper-form intake for a records office

**User:** the records-office clerk who today double-keys every paper form. **Process:** a scanned form arrives; it is
read, checked and either filed as a record or handed to a person with the failing field named. **Gain:** forms whose
own arithmetic holds are filed with no keying (49% on our difficult pilot, 0 of 462 accepted fields wrong); the rest
reach the clerk with one field, its crop and a note in Spanish and English.

Evolus is where the case lives. Our code (`evolus/`) drives it over the Evolus REST API; the decision stays with the
paper's arithmetic (our gate), never with a model.

```
masked page ──► primary read (Gemma-4-31B-IT on AMD, measured) ──► gate ─┐
           └──► Evolus document extractor (independent reader) ──► gate ─┤ compare
                                                                          ▼
                       accepted ──► Evolus knowledge library "Records register" (record_<form>.txt)
                       routed   ──► Evolus agent on Gemma-4-31B-IT/AMD drafts the clerk's note (EN)
                                    ──► AI Tool "translate" (ES)
                                    ──► Evolus workflow "Review hand-off" (case JSON: field, crop link, notes)
                                    ──► poll the run (or receive its callback) ──► status shown in our app
```

## Building blocks and what each does

| Block | Real work it does | Called from |
|---|---|---|
| **Document extractor** | Reads the masked page into the 23 schema fields: a third, independent reader. Its read goes through our gate and is compared field by field. A different read that fails the paper's arithmetic is overruled; a different read that *also* passes every identity sends the form to a person. | `evolus/case.py` `Case.run` |
| **Agent (OpenAI-compatible chat), on Gemma-4-31B-IT via AMD Token Factory** | Drafts the two-sentence note for the clerk from the gate's facts (which field, why). Told never to guess the value. | `Case.handoff` |
| **AI Tool `translate`** | Turns the note into Spanish for the Mexican records office. | `Case.handoff` |
| **Knowledge library** | The office's register: each accepted form is filed as a text record (neutral field names, values). An Evolus agent can then answer questions over the register. | `Case.file_record` |
| **Workflow "Review hand-off"** | Takes a routed case (JSON: form, fields to check, crop links, EN/ES notes) and hands it to a person; we poll its execution and show the status. Optional callback to our app. | `Case.start_workflow` |

Our gate is also exposed to Evolus: `POST /api/gate` (Bearer `TWOHANDS_GATE_TOKEN`) so an Evolus agent or workflow
step can check a form's arithmetic instead of guessing (needs the app reachable from the internet, e.g. the Docker
image on a host, and `TWOHANDS_PUBLIC_URL`).

## Endpoints used

All are documented on the one public Evolus API page, **https://evolus.ai/developers** (fetched 2026-10-15; the full
interactive reference is only inside a workspace at https://app.evolus.ai). Base: `https://api.evolus.ai`.
Auth: REST = `X-ApiKey` + `X-Application-Id`; agent chat = `Authorization: Bearer <application API key>`.

| Endpoint | Used for | Doc | Verified live |
|---|---|---|---|
| `GET /v1/models` | find the agent id (`applicationId:agentId`) | https://evolus.ai/developers (Agent chat) | yes, 200 (list empty until an agent exists) |
| `POST /v1/chat/completions` | agent drafts the clerk's note | https://evolus.ai/developers (Agent chat) | mocked in tests; needs an agent |
| `POST /api/v1/agents/{agentId}/json/{extractorId}/ask-file?useWebhook=false` | extractor reads the masked page | https://evolus.ai/developers (Document extractors) | mocked; needs EVOLUS_APP_ID + extractor |
| `GET /api/v1/ai-tools` | catalog; picks the translate option name | https://evolus.ai/developers (AI Tools) | mocked; needs EVOLUS_APP_ID |
| `POST /api/v1/ai-tools/translate/run` | EN → ES note | https://evolus.ai/developers (AI Tools) | mocked; needs EVOLUS_APP_ID |
| `POST /api/v1/memories/{libraryId}/documents?language=en` | file an accepted record | https://evolus.ai/developers (Knowledge libraries) | mocked; needs library |
| `GET /api/v1/memories/{libraryId}/documents` | `check`: list filed records | https://evolus.ai/developers (Knowledge libraries) | mocked |
| `POST /api/v1/workflows/{workflowId}/execute` (multipart: `input`, `parameters`, `callbackUrl`, `callbackMethod`, `callbackApiKey`, `callbackApiKeyName`) | start the hand-off | https://evolus.ai/developers (Workflows) | mocked; needs workflow |
| `GET /api/v1/workflows/{workflowId}/executions/{executionId}` | poll Pending / Running / Completed / Failed | https://evolus.ai/developers (Workflows) | mocked |

What the public docs do **not** offer: endpoints to *create* agents, extractors, libraries or workflows, or to
register a model. Those are set up once in the workspace UI (below); our code then drives them. We did not invent
endpoints for them.

Our side: `POST /api/gate`, `GET /api/evolus/case/{form}`, `POST /api/evolus/callback` (header `X-Callback-Key`).

## One-time setup in the Evolus workspace (UI)

1. **API keys page** of the AMDACT3 workspace: copy the **space ID** into `.env` as `EVOLUS_APP_ID`. (The
   application API key is already `EVOLUS_KEY`.)
2. **Connect the model** (Evolus: "Add the model in your workspace: base URL, model name and API key", then
   "Test the connection"): Base URL = your `AMD_BASE_URL`; Model = `Gemma-4-31B-IT`; API key = your `AMD_KEY`.
   Paste them yourself; they are never sent by our code. We checked that Gemma-4-31B-IT on the Token Factory
   returns proper `tool_calls` (function calling, which Evolus requires).
3. **Create an agent** "Intake clerk" and select that model. Instructions: *"You prepare review tasks for a
   records office that captures paper tally forms. Name the fields to check and why, in at most two sentences.
   Never guess a value; the form's arithmetic decides."* Run `python -m evolus check`; copy the listed id into
   `EVOLUS_AGENT`.
4. **Document extractor** on that agent, output JSON, named "Tally sheet type 2": add the 23 integer fields printed by
   `python -m evolus fields` (names `SOBRANTES` … `OPT01` … `TOTAL`, with their descriptions). Put the agent id and
   extractor id (from the extractor's page URL or its API tab) in `EVOLUS_EXTRACTOR_AGENT_ID` and `EVOLUS_EXTRACTOR_ID`.
5. **Knowledge library** "Records register": its id into `EVOLUS_LIBRARY_ID`.
6. **Workflow** "Review hand-off": input = text (the case JSON). Step 1: the Intake clerk agent, prompt *"Create a
   review task for the records-office reviewer from this case: {input}. Include the fields to check, the crop links
   and both notes."* Step 2: the hand-off to a person (assignment / approval / email step, whichever the workflow
   editor offers). Switch it **on** (a switched-off workflow answers 409). Its id into `EVOLUS_WORKFLOW_ID`.
7. Optional: `TWOHANDS_GATE_TOKEN` (any long random string) to enable `POST /api/gate`; `TWOHANDS_PUBLIC_URL` (where the
   app is reachable) for crop links and the workflow callback; `EVOLUS_CALLBACK_KEY` for the callback header.

Then:

```bash
python -m evolus check            # which blocks are configured; lists agents, AI Tools, library documents
python -m evolus run --pick 2,3   # 2 accepted + 3 routed masked forms -> results/evolus_runs.jsonl
```

A block that is not configured is recorded as `skipped`, never simulated.

## AMD calls caused through Evolus

Our own limiter (6 req/min, `cache/ratelimit.json`) cannot see calls Evolus makes from its servers with the same key.
Per form: agent chat = 1 call on a routed form, 0 on an accepted form; the workflow's agent step = 1 per routed form;
the extractor = 0 or 1 depending on which model Evolus reads documents with. A 5-form run is therefore at most about
11 Token Factory calls, spread over a few minutes. Each record stores `amd_calls_via_evolus` (the chat calls we
triggered directly).

## Privacy and framing

Only masked pages (`data/masked/**`) are sent; the case refuses a form without one. Vote rows are `OPT01`…`OPT15`
("Option 01"…); notes pass through the app's neutralizer; nothing is totalled by option. Keys are loaded by
`evolus/config.py`, never printed, and every log line and record is passed through `redact()`
(tests: `tests/test_evolus_flow.py`).
