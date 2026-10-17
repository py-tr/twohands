"""Captions for the video: writes slides/two-hands.srt from the script lines below (timestamps from slides/video-script.md,
split by word count). After recording, edit the bracketed number (90) to what you said and run: python scripts/make_srt.py"""
segs = [
 (0,8,["OCR reads the number.","Two Hands checks whether the whole form agrees."]),
 (8,22,["Gemma, on AMD, reads 23, in digits and in words.","The rows sum to 366, not 466.","Routed to a person.","The paper says 123."]),
 (22,33,["Every field gets a receipt.","Verified: it proves the record is unchanged.","Not that the reading is right."]),
 (33,53,["1,270 real tally sheets, read by Gemma on AMD.","49 capture errors, confirmed by the certified count.","On the state's own local actas, 91.6% field match,","where the AI tool the state bought scored 63%."]),
 (53,66,["$1 per sheet audited.","The first step: a paid shadow-mode pilot,","on one state's count in 2027."]),
 (66,91,["Measured, not promised.","300 random forms, chosen before any model read.","52 fields where the capture does not match the paper.","Then we tested the fix on 100 new forms.","Zero wrong, in 484 accepted fields.","With 95% confidence, fewer than 1 in 100."]),
 (91,116,["This is the product.","An auditor brings the typed data and the scans.","Here, the sample: 6,000 fields, checked in seconds.","267 disputes, strongest first.","Each has its photo and a receipt.","One fingerprint seals the whole report.","Change one number, and the check fails."]),
 (116,124,["A whole state: Colima.","Gemma on AMD read all 982 sheets for 14 cents."]),
 (124,140,["Now a live read.","One request to Gemma, on the AMD Token Factory.","We cut the wait. The timer stays on screen.","It took 90 seconds.","Every check holds: accepted."]),
 (140,155,["Arithmetic has no language.","I filled this practice sheet by hand, in Czech and in English.","This is a demonstration, not a measurement."]),
 (155,172,["Each strong finding becomes a case in Evolus.","The agent runs on Gemma, on AMD, and drafts the finding.","A script, not the model, scores the evidence.","The auditor decides."]),
 (172,200,["Who pays? Mexico's preliminary counts:","INE, 32 state institutes, and their outside auditors.","On 6 June 2027, 32 local elections join the federal midterm.","The pilot runs beside the state's own capture;","nothing in its process changes.","Next: 7 more countries publish these sheets,","and health reporting in 70+ countries runs on DHIS2."]),
 (200,223,["Most paper records are private, by law or by contract:","patient charts, loan files, drug registers,","so nobody can publish an error rate on them.","Mexico's tally sheets are the clearest exception:","the photo, the keyed value and the certified count are all public.","Elections are our proof set, not our only market."]),
 (223,239,["Where does it fail?","Once, the model read 3,114.","The paper says 314. One digit added.","The first gate would accept it.","Gate version two sent it to a person."]),
 (239,245,["Two Hands.","Receipts for every number keyed from paper.","Running on AMD."]),
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
