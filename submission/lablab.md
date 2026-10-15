# lablab.ai submission text

Paste each block into the matching field. Every number here is the one in `app/data/headline.json`; `make eval`
recomputes them.

## Title (42 characters)

Two Hands: receipts for every keyed number

## Short description (244 characters)

Every number keyed from paper, checked against the photo, with the photo as proof. Gemma on AMD read 300 random handwritten tally sheets and found 52 fields where the official capture differs from the paper, 22 confirmed by the certified count.

## Long description

Every number typed from a paper form, checked against the photo of that paper, with the photo as proof. A vision
model on AMD reads the form; the form's own arithmetic decides what to trust; every dispute arrives with its crop.

Measured on a pre-registered random sample of 300 handwritten tally sheets from Mexico's 2024 count, graded against
the official double-keyed capture: the model found 52 fields where the capture does not match the paper, 22 of them
confirmed by the certified count. Errors we did not plant, in a record we did not write, in a sample drawn before
any model read.

Who pays: auditors who already check the count's system, trial monitors who verify source data against charts,
internal audit of keyed files. By hand, checking numbers against paper does not pay. Here it costs $0.14 to $0.65
of AMD compute per 1,000 forms, offered at $100 per 1,000 audited. A state's count is about 1,000 to 21,000 forms
(one per polling station), so one state audit is about $100 to $2,100.

Others check the model against the source. We check the record against the paper.

Alone, the model mis-keys about 1 field in 37; the official two-person capture typed a wrong number in 1 field in
374. That is why the model never decides. The paper does, and a person sees the rest.

What runs on AMD: every measured read of the 300 is Gemma-4-31B-IT on AMD GPUs through AMD Token Factory, one
request per form, at $0.000144 and 87 s per form on the shared endpoint. Qwen3.8-27B on the same endpoint is the second reader. The organisers withdrew Gemma from the endpoint on 15
October, so live reads in the app now use Qwen3.8-27B on AMD. Page locating, the privacy mask and the gate run on
CPU.

Limits: the gate accepts only 18% of forms with no person (1 field in 605 wrong on those);
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
