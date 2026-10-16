"""Captions for the video: writes slides/two-hands.srt from the script lines below (timestamps from slides/video-script.md,
split by word count). After recording, edit the bracketed numbers (310, 90) to what you said and run: python scripts/make_srt.py"""
segs = [
 (0,10,["The paper says 175.","The official capture typed 75.","The certified count says 175."]),
 (10,20,["Two Hands checks every number typed from paper, against the paper.","On AMD, 310 forms audited so far."]),
 (20,40,["Pick any polling station. 169,000 of them.","This one we have read: the page and its receipts, at once.","This one, not yet.","One click, and the reader on AMD takes it next."]),
 (40,60,["How does it work? Two hands.","The model on AMD reads every number twice: the digits, and the words.","Then the gate: the form's own arithmetic.","If it all adds up, nobody types anything.","If not, a person sees the rest, with the photo."]),
 (60,85,["Measured, not promised.","300 random forms, chosen before any model read.","52 fields where the capture does not match the paper.","Then we tested the fix on 100 new forms.","Zero wrong, in 484 accepted fields.","That is not proof of zero. It means: fewer than 1 in 100."]),
 (85,110,["This is the product.","An auditor brings the typed data and the scans.","Here, the sample: 6,000 fields, checked in seconds.","267 disputes, strongest first.","Each has its photo and a receipt.","One fingerprint seals the whole report.","Change one number, and the check fails."]),
 (110,130,["Now a live read.","One request to Gemma, on the AMD Token Factory.","We cut the wait. The timer stays on screen.","It took 90 seconds.","Every check holds: accepted."]),
 (130,145,["Arithmetic has no language.","I filled this practice sheet by hand, in Czech and in English.","This is a demonstration, not a measurement."]),
 (145,162,["Each strong finding becomes a case in Evolus.","The agent runs on Gemma, on AMD, and drafts the finding.","A script, not the model, scores the evidence.","The auditor decides."]),
 (162,193,["Who pays?","Three lines from INE's own files.","One: on 6.5% of stations, two official records of one paper disagree.","Two: almost one form in five fails its own row sum.","Three: the audit checks the software, not the typed numbers.","INE tried to buy a machine first capture: MXN 9.5 million, an 80% bar.","Auditors and PREP operators buy the check, at $1 per form."]),
 (193,219,["Most paper records are private, by law or by contract:","patient charts, loan files, drug registers,","so nobody can publish an error rate on them.","Mexico's tally sheets are the clearest exception:","the photo, the keyed value and the certified count are all public.","That's why we measured there.","Elections are our proof set, not our only market."]),
 (219,239,["Where does it fail?","Once, the model read 3,114.","The paper says 314. One digit added.","The first gate would accept it.","Gate version two sent it to a person."]),
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
