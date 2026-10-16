# lablab.ai submission text

Paste each block into the matching field. Every number here is the one in `app/data/headline.json`; `make eval`
recomputes them.

## Title (42 characters)

Two Hands: receipts for every keyed number

## Short description (253 characters)

Gemma on AMD read 300 random handwritten tally sheets: 52 fields where the official capture differs from the paper, each with its photo. One reader accepts 18% of forms with no person, 2 wrong fields in 1,210; two that must agree: 30%, 0 wrong in 1,958.

## Long description

Every number typed from a paper form, checked against the photo of that paper, with the photo as proof. Others
check the model against the source. We check the record against the paper. A vision model on AMD reads the form;
the form's own arithmetic decides what to trust; every dispute arrives with its crop.

Two hands: two independent readers, and the paper's own arithmetic as the referee.

Measured on a pre-registered random sample of 300 handwritten tally sheets from Mexico's 2024 count, graded against
the official double-keyed capture: the model found 52 fields where the capture does not match the paper, 22 of them
confirmed by the certified count. Errors we did not plant, in a record we did not write, in a sample drawn before
any model read.

Mexico's rule already asks for this job. In INE's PREP process every tally sheet gets a second capture by a
person, and the system compares it with the first; a mismatch goes to a third capture, then a verification centre,
and published data are later checked against the sheet in the cotejo (Proceso Técnico Operativo 2023-2024,
numerals 30 to 35; the same phases bind all 32 state PREPs through Anexo 13 of INE's Reglamento de Elecciones).
Two Hands is that second capture: a model, refereed by the paper, with a receipt for every field. After all of
those steps, 0.8% of fields in our random sample still do not match the paper (52 of 6,358, at least); our second
capture puts 1 in 5 of its disputes on a confirmed capture error.

Who pays: the regulated second capture. PREP operators and vendors, who pay people for it today, and the state
institutes (OPLEs) that contract them; then the outside auditors, for an audit of a finished capture. Clinical
trials, insurance claims and customs declarations are the next market, not measured. Numeral 33 names a person, so
a model as the second capture is a change the institute must approve: we show evidence, not compliance. It costs
$0.14 to $0.65 of AMD compute per 1,000 forms, offered at $100 per 1,000: compute is under 1% of the price, which
also covers review labour for routed fields, hosting and sales. A state's count is about 1,000 to 21,000 forms (one
per polling station), so one state is about $100 to $2,100.

When an agent keys a form, the paper still has to agree. Receipts work the same for a model as for a person; in our
measurement, Gemma is the agent.

One reader: 18% of forms with no person, 2 wrong fields in 1,210. Two readers that must agree, with the paper's sums as referee: 30%, 0 wrong in 1,958. Both pre-registered; the one-reader figure is the primary.
(The two-reader tier checks words = digits and row sums, without the section checks.)

Alone, one model mis-keys 1 field in 37. Two models that agree, refereed by the paper, mis-keyed 0 of 1,958.

What runs on AMD: every measured read of the 300 is Gemma-4-31B-IT on AMD GPUs through AMD Token Factory, one
request per form, at $0.000144 and 87 s per form on the shared endpoint. Gemma-4-31B-IT is the primary reader in every mode: it reads every form, accepts the most forms alone (55 against Qwen's 31), and costs a quarter of the second reader. In two-reader mode a second model must agree with Gemma field by field before the paper's arithmetic accepts; the second reader never overrides Gemma, it only withholds acceptance. Live reads in the app use Gemma-4-31B-IT on the Token
Factory too: it is back there since 2026-10-16 02:06 UTC, after it was unavailable from 2026-10-15 15:41 UTC
(endpoint log), when live reads used Qwen3.8-27B. Page locating, the privacy mask and the gate run on
CPU.

Limits: one reader accepts only 18% of forms with no person (1 field in 605 wrong on those), two readers 30%;
the rest are routed. The row-label check is costly: it routed 86 forms, and on 68 of them the read matched the paper on every field. 11 of the 300 pages could not be located and went to a person before
any model call. Recall is measured on a small set (7 of 7).

An independent demonstration of clerical capture quality, not an official INE product. Vote rows are shown as
Option 01 to Option 15. "Capture error" means the capture does not match the paper.

## Links

Live demo: add at submission · Video: add at submission · Audit report sample: add at submission · How to
reproduce: `make eval` in the repo

## Technology tags

AMD Token Factory, AMD GPUs, Gemma, Gemma-4-31B-IT, Qwen3.8-27B, Evolus, Python, FastAPI, OpenCV,
vision language model, document verification, data quality, audit

## Tracks

- AMD (main track)
- Google DeepMind Gemma (best use of Gemma models on AMD GPUs)
- Evolus (Business Agents)
