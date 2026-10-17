# Colima recall check (PROTOCOL.md Amendment 9)

Recall check (Amendment 9): 139 fields where the certified count differs from the capture and Gemma agreed with the capture; a person's blind check is in progress at /check?set=colimarecall.

Rule: graded field the certified count covers (vote rows, TOTAL), on a form settled by cotejo not recount; candidate: certified differs from the capture and Gemma equals the capture; caught: certified differs from the capture and Gemma equals the certified count; neither: certified differs from both.

Forms read: 982. Candidates: 139. Caught (colima_audit.json): 27. Certified differs from both (not counted): 2.

In progress: answers come from the blind page /check?set=colimarecall; nothing is reported until every candidate is answered.

Built by `scripts/colima_recall.py` (build, score); crops in `results/colima/recall_crops/`.
