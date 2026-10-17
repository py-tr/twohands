# IEEBCS head-to-head: run record (PROTOCOL_IEEBCS.md sections 4 and 8)

**Deviation (recorded 2026-10-17, before scoring):** section 4 asks for this file to be written before the first
read. It was not; it is written now from the run's own records (`calls_gemma.jsonl`, `run.log`, `run_status.json`),
which carry the served model id and the prompt hash on every row. Nothing about the run is changed by it.

- Reader: Gemma-4-31B-IT, temperature 0, one read per acta, served by **AMD Token Factory** (served model id on all
  300 call records: `Gemma-4-31B-IT`; no row carries the self-hosted vLLM id `google/gemma-4-31B-it`, so no row is
  called an MI300X read). vLLM version: not applicable (Token Factory).
- Protocol file last committed: e520725, 2026-10-16 08:57 UTC. Run: start 2026-10-16 14:55:57 UTC, last read
  17:25:15 UTC, 300 of 300 actas (294 read and parsed, finish "stop"; 6 no call: 5 special-station actas not covered,
  1 page the locator rejected), 52 accepted by the gate.
- Prompt hashes on the call records: exactly the four pre-registered in section 4.
- Plumbing check (section 11): `plumbing_check.md`, 5 actas, confirmed by a person on 2026-10-17, mapping correct,
  no fix to the join/mapping code.
- Second reader (Qwen): not run.
