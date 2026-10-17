"""Captions for the video: writes slides/two-hands.srt from the script lines below (timestamps from slides/video-script.md,
split by word count). After recording, edit the bracketed number (90) to what you said and run: python scripts/make_srt.py"""
segs = [
 (0,10,["Two Hands.","Verifiable quality control for handwritten numbers.","OCR reads the number.","Two Hands checks whether the whole form agrees."]),
 (10,28,["Mexico counts every tally sheet twice:","a fast preliminary capture, then the certified count.","On 6.5% of the polling stations not recounted,","the two official records of the same paper disagree."]),
 (28,40,["And 19.2% of national forms fail their own row sum,","in the official capture.","A sum says something is wrong; the photo says which field."]),
 (40,60,["Gemma, on AMD, reads every field twice:","the digits and the amount in words.","A second, independent reader must agree.","The referee is the paper's own arithmetic.","Every check holds: accepted.","One fails: a person sees the field, with its photo."]),
 (60,72,["Here is a real sheet.","Gemma read 23, in digits and in words.","But the rows sum to 366, not 466."]),
 (72,84,["On the site, the same sheet: routed to a person.","The paper says 123, and with it the sum holds."]),
 (84,94,["Every field gets a receipt.","Verified: it proves the record is unchanged.","Not that the reading is right."]),
 (94,110,["Now a live read.","One request to Gemma, on the AMD Token Factory.","We cut the wait; the timer stays on screen.","It took 90 seconds.","Every check holds: accepted."]),
 (110,138,["This is the product.","An auditor brings the typed data and the scans.","Here, the sample: 6,000 fields, checked in seconds.","267 disputes, strongest first.","This one: the capture keyed 75; the paper says 175.","One fingerprint seals the whole report.","Change one number, and the check fails."]),
 (138,150,["The proof.","Gemma on AMD read 1,270 real handwritten tally sheets.","49 capture errors, confirmed by the certified count."]),
 (150,165,["On Baja California Sur's local actas: 91.6% field match.","The Google Document AI reading the state bought","scored 62.84%, on the same metric."]),
 (165,178,["Recall: 27 of 28 capture errors the certified count reveals,","in one state, pre-registered.","A person re-read the AI-judged disputes blind:","0 read differently."]),
 (178,200,["Same 300 forms, same gate.","It accepts 1.8x the forms Qwen does, at the same error rate,","4.6x cheaper, 2.8x faster.","A whole state: Colima.","Gemma on AMD read all 982 sheets for 14 cents."]),
 (200,215,["Each strong finding becomes a case in Evolus.","The agent runs on Gemma, on AMD, and drafts it.","A script, not the model, scores the evidence.","The auditor decides."]),
 (215,236,["Who pays? Mexico's preliminary counts:","INE, 32 state institutes, and their outside auditors.","On 6 June 2027, 32 local elections join the federal midterm.","$1 per sheet audited, proposed.","The first step: a paid shadow-mode pilot on one state's count."]),
 (236,248,["Next: 7 more countries publish these sheets,","and health reporting in 70+ countries runs on DHIS2.","Elections are our proof set, not our only market."]),
 (248,254,["Two Hands.","Verifiable quality control for handwritten numbers.","Running on AMD."]),
]
def ts(t):
    ms=int(round(t*1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
out=[];i=1
for a,b,lines in segs:
    w=[len(l.split())+1 for l in lines]; tot=sum(w); t=a
    for l,k in zip(lines,w):
        e=t+(b-a)*k/tot
        out.append(f"{i}\n{ts(t)} --> {ts(e-0.05)}\n{l}\n"); i+=1; t=e
open("slides/two-hands.srt","w",encoding="utf-8").write("\n".join(out))
print(i-1)
