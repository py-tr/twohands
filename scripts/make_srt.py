"""Captions for the video: writes slides/two-hands.srt from the script lines below (timestamps from slides/video-script.md,
split by word count). After recording, replace [N] in "It took [N] seconds." with the measured seconds you said
(shown on screen) and run: python scripts/make_srt.py"""
segs = [
 (0,23,["Two Hands.","Verifiable quality control for handwritten numbers.","It's built first for the institutes","that run Mexico's vote counts, and their auditors.","OCR reads the number.","Two Hands checks whether the whole form agrees.","Here, the official record typed 480.","The paper says 180.","Gemma read the paper."]),
 (23,40,["Mexico counts every tally sheet twice:","a fast preliminary capture, then the certified count.","On 6.5% of the polling stations not recounted,","the two official records of the same paper disagree."]),
 (40,66,["Here is a real sheet.","Gemma misread one field as 23, in digits and in words.","The paper's own arithmetic catches it:","the rows sum to 366, not the 466 total.","So it is not accepted: it goes to a person, with the photo.","The paper says 123."]),
 (66,76,["Every field gets a receipt.","Verified: it proves the record is unchanged.","Not that the reading is right."]),
 (76,94,["Gemma, on AMD, reads every field twice:","the digits and the amount in words.","The referee is the paper's own arithmetic.","Every check holds: accepted.","One fails: a person sees the field, with its photo."]),
 (94,110,["Now a live read.","One request to Gemma, on the AMD Token Factory.","I cut the wait; the timer stays on screen.","It took [N] seconds.","Every check holds: accepted."]),
 (110,138,["This is the product.","An auditor brings the typed data and the scans.","Here, the sample: 6,000 fields, from the stored AMD reads,","checked in seconds.","267 disputes, strongest first.","This one: the capture keyed 75; the paper says 175.","One fingerprint seals the whole report.","Change one number, and the check fails."]),
 (138,153,["Each strong finding becomes a case in Evolus.","The agent runs on Gemma, on AMD, and drafts it.","A script, not the model, scores the evidence.","The auditor decides."]),
 (153,176,["The proof.","Gemma on AMD read 1,270 real handwritten tally sheets.","49 capture errors, confirmed by the certified count.","Recall: 27 of 28 capture errors the certified count reveals,","in one state, pre-registered.","A person re-read the AI-judged disputes blind:","0 read differently."]),
 (176,196,["On Baja California Sur's local actas: 91.6% field match.","The Google Document AI reading the state bought","scored 62.84%.","Same per-field metric: theirs on all 2,020 actas,","ours on a random 300."]),
 (196,216,["Same 300 forms, same gate.","It accepts 1.8x the forms Qwen does,","4.6x cheaper, 2.8x faster.","A whole state: Colima.","Gemma on AMD read all 982 sheets for 14 cents."]),
 (216,268,["The auditor looks at 4% of the fields, each with its photo.","On 6 June 2027, 32 local elections join the federal midterm.","$1 per sheet audited, proposed:","for Morelos, half a percent of what it paid to run its count.","The first step: a paid shadow-mode pilot on one state's count.","The check is the form's own arithmetic,","so it isn't tied to elections.","Proven on two form types: Mexico's tally sheets","and UK rainfall ledgers (1850-1960), no retraining.","Next: tally sheets in at least 7 more countries","that publish their images,","and the monthly health-facility reports behind DHIS2,","used in 70+ countries."]),
 (268,278,["Every number re-derives from public data, with one command.","Two Hands.","Verifiable quality control for handwritten numbers.","Running on AMD."]),
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
