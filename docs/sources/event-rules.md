# Event rules we cite, with their public sources

Excerpts of the hackathon rules and organiser statements that the docs in this repo rely on. Quotes are verbatim as
fetched or as posted; the date is when we read them. Discord messages have no public URL; each is given with its date,
channel or server and the author's role.

## Public pages

| Source | URL |
|---|---|
| Event page, AMD Developer Hackathon: ACT III (lablab.ai) | https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii |
| Event live page | https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live |
| lablab hackathon guidelines (submission guide) | https://lablab.ai/ai-articles/hackathon-guidelines |
| lablab Terms of Use | https://lablab.ai/terms-of-use |
| Kickoff recording | https://www.youtube.com/watch?v=gqUj24Gtdr0 |
| Evolus hackathon blog post | https://evolus.ai/en/blog/evolus-amd-developer-hackathon-lablab |
| Evolus hackathon conditions | https://evolus.ai/en/hackathon-conditions |
| Evolus developer docs | https://evolus.ai/developers |
| Evolus event workspace join link (event code AMDACT3) | https://app.evolus.ai/join/AMDACT3 |
| AMD Token Factory (API keys, model catalogue; sign-in required) | https://notebooks.amd.com/tokenfactory |

## Event page (read 2026-10-12 to 2026-10-15)

- Gate: "AMD is a required technology to be eligible for prizes." / "The AMD component must be part of the working
  product shown to the judges."
- "Submissions must be original and MIT-compliant."
- Organiser checklist (in the page source, 2026-10-13): "Code: Public repository · Setup and run instructions ·
  Application or demo link when available · Simple architecture diagram. AMD evidence: AMD hardware or infrastructure
  used · Model and serving stack · At least one relevant benchmark · A clear explanation of what ran on AMD.
  Evaluation: One business result · One known limitation · One failure case · The safeguard or human review process.
  Note: Do not include credentials, API keys, confidential information, or personal data in a public repository."

### Evolus track ("Evolus Business Agents on AMD")

- "Build an AI agent that runs a real business process end to end, on Evolus, powered by an open model served on AMD.
  [...] The agent takes the input (an email, a PDF, a recording, a web form, a chat), reasons over it with an open
  model running on AMD, and acts: it runs an Evolus workflow, turns documents into data, uses AI Tools, updates another
  system, or hands the case to a person when it should."
- Requirements: "Build in a free Evolus event workspace, created at app.evolus.ai with the event code shared at
  kickoff." · "Bring your own model: the main agent must use an open model served on AMD infrastructure through your
  own vLLM endpoint on AMD Developer Cloud." · "Use at least two Evolus building blocks: workflows, document
  extractors, AI Tools, knowledge libraries, MCP connectors, sub-agents, chat widget." · "Drive Evolus from your app
  through its APIs: the Evolus REST API for workflows, extractors, AI Tools and libraries; agent chat through the REST
  API or the OpenAI-compatible endpoint." · "Follow the hackathon submission rules: containerized app, public GitHub
  repository, a README that runs. Never commit API keys: use environment variables."
- Evolus block, page refresh of 2026-10-13: "Bring your own model. Event workspaces run their agents on the model each
  team connects: an open model through a vLLM endpoint on AMD Developer Cloud, or any OpenAI-compatible provider."

## Kickoff (2026-10-12, recording above)

- Evolus CTO: event workspaces are free "until November 15th, so the judges can try your demo".
- Host: "make it clear which part runs on AMD and what that part does".

## Discord statements (lablab.ai Discord server)

| Date (UTC) | Author (role) | Statement |
|---|---|---|
| 2026-10-13 | lablab organisers, #announcements | "ACTIII is hosted on notebooks.amd.com/tokenfactory - there is no billing or credit card info needed there" · "Developers dont need the $100 credit to participate in the ActIII hackathon. Just the api from the tokenfactory." |
| 2026-10-14 | Maharshi (AMD, admin) | "no, its not a requirement to use it on AMD dev cloud. In fact, we are giving free apikeys for teams registered for lablab ActIII on notebooks.amd.com/tokenfactory" |
| 2026-10-14 | lablab organisers, #announcements | Google DeepMind joins: "You can now build with Gemma, Google DeepMind's family of open models, running on AMD GPUs [...] Teams building with Gemma can compete for a dedicated Google prize" |
| 2026-10-15 ~18:11 | Maharshi (AMD, admin) | "folks with gemma4 issues, the team is currently reviewing and will get back. for hackathon no cloud credits needed only apikey from notebooks.amd.com/tokenfactory." |
| 2026-10-16 | LazyLoad (Evolus team) | A custom MCP server can be added manually from the workspace's Connectors page; the Evolus workspace name must be shown clearly in the app or the presentation; the workspace and the model endpoint must stay online until Nov 15 for evaluation; for a dockerized app: README with docker compose, `.env.example`, video end to end. (Paraphrase of several messages.) |
| 2026-10-16 | LazyLoad (Evolus team) | "Token Factory works fine on Evolus and does count for the Track." |
