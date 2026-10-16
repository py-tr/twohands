# Business case

Every PREP tally sheet in Mexico is already captured twice and compared, by rule. Two Hands is an automated capture
with a referee: a vision model on AMD, refereed by the paper's own arithmetic, with a receipt (the crop) for every field
it disputes. What we sell for 2027 is that engine as an independent check of a finished capture.

**One product, one buyer, for 2027.** Who pays in 2027: the PREP's outside auditor or its contracted operator, for an independent check of a finished capture, field by field against the photo. It needs no rule change: it is an outside check, which is what we measured. A model as the regulated second capture (PTO numeral 33) needs the institute's governing body to approve it after INE's opinion (RE art. 339); that is the longer-term path, not the 2027 product.

Which form: state institutes (OPLEs) process local actas (governor, local deputies, municipalities). The presidential forms we measured (and the Senate forms we read) are federal, processed by INE. Our local evidence is the Baja California Sur head-to-head on local actas (PROTOCOL_IEEBCS.md): read on AMD, not yet scored: no result is shown until it is.

Status: no buyer contacted yet.

Every number here is either **measured** (we cite the file in this repo) or **cited** (we fetched the source and
quote it). Anything beyond elections is labelled **next market, not measured**. One exchange rate throughout:
MXN 18.3835 per USD (ECB, 2026-10-16) (https://api.frankfurter.app/latest?from=USD&to=MXN (ECB reference rate, fetched 2026-10-16)).

**In three sentences.** The problem: INE's two official captures of the same paper disagree on 6.5% of the polling stations that were not recounted, and 19.2% of captured forms fail their own row sum. The gap: the mandated audit checks the software, not the keyed values. The appetite: INE tried to buy an automated first capture in 2024 (an MXN 9.5M draft line, unspent), set an 80% bar that no entrant met, and its advisers asked for a pilot.
(Sources: "The cost of the problem" below; INE CCOE report pp. 4, 5, 10; RE art. 347.)

## 0. The regulated process

### The text

INE's *Proceso Técnico Operativo del Programa de Resultados Electorales Preliminares para el Proceso Electoral
Federal 2023 – 2024* (PTO), annex to the Consejo General's extraordinary session of November 2023, file
`CGex202311-03-ap-8-a.pdf`:
<https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/155635/CGex202311-03-ap-8-a.pdf>
(fetched 2026-10-16; quotes copied from the PDF text, page numbers as printed on it).

**Numeral 1 (p. 1), who it binds.**
> "El presente proceso técnico operativo es de observancia general y obligatorio para el Instituto Nacional
> Electoral, así como para las personas que participen en cada una de sus fases en el Proceso Electoral Federal
> (PEF) 2023 - 2024."

*This technical operating process is of general and mandatory observance for the INE and for the people who take
part in any of its phases in the 2023-2024 federal election.*

**Numeral 30 (p. 8), the first capture may be automatic.**
> "La imagen del Acta PREP podrá ser procesada a través de la captura automática y registrará los datos detectados
> correspondientes a los resultados de la votación, boletas sobrantes, total de personas que votaron, total de
> representaciones de partidos políticos y de candidaturas independientes acreditadas ante casilla que votaron y
> total de votos sacados de la urna. En este caso, la captura automática será considerada como primera captura del
> Acta PREP."

*The image of the Acta PREP may be processed through automatic capture, which will record the detected data for
the vote results, unused ballots, total people who voted, total party and independent-candidate representatives
who voted, and total votes taken from the ballot box. In that case, the automatic capture is considered the first
capture of the Acta PREP.*

**Numeral 33 (p. 8), the second capture and the comparison.**
> "Concluida la primera captura del Acta PREP, de manera automática el sistema asignará a una persona
> capturista/verificadora la imagen de la misma Acta PREP para realizar la segunda captura de los datos asentados
> en esta. El sistema hará una verificación comparando que los datos registrados en la primera captura coincidan
> con los de la segunda. Si todos los datos son iguales, la fase de captura y verificación de esa Acta PREP
> concluye."

*Once the first capture of the Acta PREP is done, the system automatically assigns the image of the same Acta PREP
to a capturist/verifier to make the second capture of the data written on it. The system verifies by comparing
that the data recorded in the first capture match those of the second. If all the data are equal, the
capture-and-verification phase of that Acta PREP ends.*

**Numerals 34 and 35 (pp. 8-9), on mismatch: a third capture, then the Verification Centre.**
> "34. En caso de que los datos registrados previamente no coincidan, el sistema enviará la imagen de manera
> automática a otra persona capturista/verificadora, para registrar nuevamente los datos que presentaron
> inconsistencias. El sistema comparará los datos registrados en la tercera captura, con los datos registrados en
> las capturas anteriores, sí coinciden en su totalidad con alguna de éstas, concluirá la fase de captura y
> verificación de esta Acta."
>
> "35. Si algún dato registrado en la tercera captura es diferente a las anteriores, la imagen del Acta PREP será
> asignada al Centro de Verificación para su resolución."

*34. If the data recorded so far do not match, the system automatically sends the image to another capturist/
verifier to record again the data that were inconsistent. The system compares the third capture with the earlier
captures; if it matches one of them entirely, the capture-and-verification phase of this Acta ends.
35. If any datum of the third capture differs from the earlier ones, the image of the Acta PREP is assigned to the
Verification Centre for resolution.*

**Numeral 4, phase f) (pp. 3-4), cotejo.**
> "f) Cotejo de actas. Tiene por objeto corroborar que los datos publicados coincidan con los datos asentados en el
> Acta PREP. El personal asignado al cotejo compara los datos y la imagen publicados en el portal del PREP, o en su
> caso, con el Acta PREP física que posee el CATD y los datos que hayan sido publicados, en caso de identificar un
> error en la captura, se podrá realizar el procedimiento para asentar los datos correctos posteriormente."

*f) Cotejo (collation) of actas. Its purpose is to corroborate that the published data match the data written on
the Acta PREP. The staff assigned to cotejo compare the data and image published on the PREP portal, or the
physical Acta PREP held at the CATD, with the published data; if they identify a capture error, the procedure to
record the correct data may be carried out afterwards.*

The same document also defines cotejo at numeral 3 j) ("Fase que permite corroborar que los datos publicados
coincidan con los datos asentados en el Acta PREP, a través del registro del resultado de esta actividad en el
sistema informático"), and at numeral 45 records each acta as "correcta" or "incorrecta"; an incorrect acta goes
back to digitalización or captura "hasta que sea marcada como correcta en cotejo".

### The same steps bind all 32 state PREPs

The PTO above is INE's own (federal). Each state institute (OPL) runs its own PREP under the **Reglamento de
Elecciones** (RE) and its **Anexo 13, Lineamientos del PREP**:

- **RE art. 336, numeral 1:** the PREP chapter's provisions "son aplicables para el Instituto y los opl". **Art. 346, numeral 1:** the
  PREP computer system, "ya sea propio o desarrollado por terceros", "deberá contemplar las etapas mínimas del
  proceso técnico operativo, señaladas en el Anexo 13". **Art. 339, numeral 1, inciso d):** each governing body
  must approve its proceso técnico operativo "al menos cinco meses antes del día de la Jornada Electoral",
  covering at least "la captura y verificación de datos"; **numeral 2:** before approval it goes to INE for its
  opinion. Source: the consolidated *Reglamento de Elecciones, Texto Vigente*, INE, September 2026 (amendments
  through INE/CG548/2026), <https://sidj.ine.mx/restWSsidj-nc/app/doc/662/20/1>.
- **Anexo 13, numeral 15** (the minimum phases), fractions III and IV:
  > "III. Captura de datos. En esta fase se registran los datos plasmados en las Actas PREP, así como la fecha y
  > hora de su registro [...]"
  >
  > "IV. Verificación de datos. Tiene por objeto corroborar que todos los datos capturados coincidan con los datos
  > asentados en cada una de las Actas PREP [...]"

  *III. Data capture: the data written on the Actas PREP are recorded, with the date and time. IV. Data
  verification: its purpose is to corroborate that all the captured data match the data written on each Acta
  PREP.*
- **Anexo 13, numeral 21** (the minimum roles), fractions III and IV:
  > "III. La o el capturista de datos: a) Registra los datos plasmados en las Actas PREP, por medio del sistema
  > informático de captura desarrollado o implementado."
  >
  > "IV. La o el verificador: a) Verifica que los datos capturados en el sistema informático, incluidos los de
  > identificación del Acta PREP, coincidan con la información plasmada en el Acta PREP digitalizada;"

  *III. The data capturist records the data written on the Actas PREP through the capture system. IV. The
  verifier checks that the data captured in the system, including the acta's identification, match the
  information on the digitised Acta PREP.*

  Anexo 13 text: the "debe decir" column of INE/CG825/2022, Anexo 1, pp. 33-34 and 38-39,
  <https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/146752/CGor202211-29-ap-25-a.pdf>.
  INE's Dirección Jurídica lists INE/CG825/2022 (29 Nov 2022) as the latest modification of Anexo 13
  (<https://ine.mx/wp-content/uploads/2025/02/DJ-Anexos-ReglamentoElecciones-05-02-25.pdf>, list as of 5 Feb 2025).
  The September 2026 consolidated Reglamento does not reprint its annexes, so we could not confirm that no 2025-2026
  agreement changed Anexo 13 since.

**Not verified, left out.** Anexo 13 fixes the minimum phases and roles. The exact mechanics (a second capture, a
third on mismatch, a verification centre) are written in each institute's own PTO. We quote INE's federal PTO; we
did not read the 32 state PTOs, and we do not claim each one copies numerals 33 to 35.

### The official process, step by step

1. **Digitalización.** The Acta PREP is photographed at the polling station (PREP Casilla) or scanned at the CATD;
   a hash is computed and the image goes to the CRID (PTO numerals 4 c), 23-28).
2. **First capture**, automatic (numeral 30) or by a capturista at a TCA (numerals 31-32).
3. **Second capture** of the same image by a person, a capturista/verificador (numeral 33).
4. **Comparison** by the system; if every datum is equal, done (numeral 33).
5. **Third capture** of the inconsistent data by another person; done if it matches an earlier capture in full
   (numeral 34).
6. **Centro de Verificación** resolves what the third capture did not (numeral 35; definition 3 g).
7. **Cotejo**, after publication: the published data against the Acta PREP; a capture error found here is
   recaptured (numerals 4 f), 44-45).

## 0b. Where Two Hands fits

Two Hands does the work of a second capture with a model, refereed by the paper, with a receipt for every field, for
the cotejo. For 2027 it runs beside the regulated steps, as an independent check of the finished capture; it does not
replace the person numeral 33 names.

| Regulated step (PTO numeral) | Two Hands |
|---|---|
| Digitalización (4 c), 23-28) | uses the same image; locates the page and masks the names-and-signatures column |
| First capture, automatic or human (30-32) | untouched; Two Hands takes the first capture as given |
| Second capture by a person (33) | **the model reads every field twice, digits and Spanish words, plus each row's printed label** |
| Comparison (33) | **field by field against the first capture; agreement plus the paper's own identities (words = digits, rows sum to the total) accepts** |
| Third capture on mismatch (34) | **only the disputed fields go to a person, ordered by evidence (strong, medium, weak), each with its crop** |
| Centro de Verificación (35) | receives the fields the paper itself does not settle (words and digits disagree, corrections) |
| Cotejo (4 f), 44-45) | **a receipt for every disputed field: crop, first capture, model digits and words, a mark, a CSV** |

The measured case, on INE's own published 2024 capture:

> In the preliminary capture (PREP, before the certified count's cómputos and before any later cotejo correction), at
> least 0.8% of fields in our random sample do not match the paper (52 of 6,358); 1 in 5 of the fields our check
> disputes is a capture error (22 confirmed by the certified count, 30 judged from the photo by the AI adjudicator, the
> builder's model, which could see both values). The certified count later agrees with the paper on 22 of the 31 it
> covers.

Sources: `app/data/headline.json` (`keying_errors` 52, `fields` 6,358, `disagree` 267; 52 / 6,358 = 0.82%;
52 / 267 = 19.5%) and `results/adjudication/SUMMARY.md`. The sample is the pre-registered random 300 presidential
tally sheets of 2024 (289 read); the capture is the published PREP 2024 CSV (the preliminary capture, cut 2024-06-03 20:05), the output of the capture and verification steps above, before the cómputos. The
52 are 17 wrong numbers typed, 27 readable fields recorded as illegible (23 on two faint forms), 6 numbers typed
where the paper is blank, and 2 readable fields captured as "no data". "At least", because a field the model did
not dispute was not examined.

**Scope, honestly.** Numeral 33 assigns the second capture to "una persona capturista/verificadora". A model as the
second capture would be a change to the proceso técnico operativo that the institute's governing body must approve
(RE art. 339.1 d), after INE's opinion (art. 339.2). We show evidence, not compliance. Two uses need no change to
the text: a model as the automatic first capture, which numeral 30 already allows, and an outside check of a
finished capture, which is what we measured.

### Institutes already tried to buy machine reading

Evidence of demand and of a public bar, not a budget for our product. Source for the four lines: INE, PREP PEF 2023-2024, 'Captura Automática' report, CCOE 10th session 26-08-2024, https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/176400/ccoe-10se-26-08-2024-p17-1.pdf (page numbers are the report's own "N de 10").

- INE put MXN 9.5M in its 2024 draft budget for an automated first capture service (PTO numeral 30), a different step from our check, and bought none (last line). (p. 4)
- IPN quoted MXN 19.9M for the service. (p. 4)
- The acceptance bar was 80% agreement on words and digits. (p. 5)
- The best entrant reached 75%; INE declined it as untested in a real election, and its advisers (COTAPREP) recommended a pilot. (pp. 5, 10)

**Our engine is an automated capture with a referee. For 2027 we offer an independent check of a finished capture, which needs no rule change; the capture inside the loop is the pilot COTAPREP requested, offered as a pilot on 2024's own forms.**

On that metric as we read it, Gemma's existing reads of our pre-registered 300 agree with the official capture in words and digits on 83.5% of fields (5,508 of 6,600; failed reads and blank or illegible captures count against us).
*INE's 2024 acceptance metric as we read it from the report, computed on our existing reads after they were made; the definition was committed before computation; not the same test set or conditions as INE's trial.*

Beside it, the result that decides acceptance: 0 wrong of 1,958 accepted fields (two readers, the paper's sums as referee), judged against the official capture; every disagreement checked on the photo; fields where the model and the capture agree were not individually checked. (`results/two_reader_300.md`). Definition: `results/ine_metric_DEFINITION.md`, committed before the computation; result and secondary rows: `results/ine_metric.md`. This is not a result on INE's test set: different images, whole pages, and a reference (the official capture) with its own errors.

Then, in order:

1. Morelos paid MXN 26.6M for its 2024 PREP: 7,802 actas expected, 110 capture-and-verification posts, and an MXN 1.5M outside audit of the system, which by rule checks the software, not the keyed values against the paper. We check every value for $1 per acta, about 9.5% of Morelos's audit line and 0.5% of its PREP cost per acta (MXN 3,409, ~$185). Source: IMPEPAC, Informe Final PREP 23-24 v2.0, p. 56, https://impepac.mx/wp-content/uploads/2024/07/Informe%20Final%20PREP_23-24_V_2.0.pdf; audit scope: RE art. 347 numeral 1; INE's 2024 audit (UAM-I), PDF p. 7, https://ine.mx/wp-content/uploads/2024/06/2024-PREP-InformeFinalAuditoriav1.pdf.
2. Baja California Sur bought an AI first capture by direct award (Google Document AI, MXN 93,834.49); it matched the human capture on 2.88% of actas and 62.84% of fields. A machine already keys; the question is who referees it. Source: IEEBCS, Informe final del PREP 2023-2024, pp. 19 and 31, https://www.ieebcs.org.mx/documentos/acuerdos/INFORME_FINAL_PREP_PLE_2023-2024.pdf.
3. Every state institute decides whether to run its PREP alone or with a third party at least six months before election day: for 6 June 2027, by about 6 December 2026. Guerrero has already decided: in-house, "con acompañamiento de un ente especializado". Source: Anexo 13 numeral 33 punto 7, as cited in IEPC Guerrero Acuerdo 057/SO/16-07-2026, considerando XI and XXVI-XXVII, https://www.iepcgro.mx/principal/uploads/gaceta/2026/7ord/acuerdo057.pdf.
4. The 2027 buyer is the outside auditor or the contracted PREP operator, paid by the state institute (OPLE). At least 13 of the 17 outsourced 2024 state PREPs went to three firms: Informática Electoral S.C. (at least 8 states), Grupo Proisi (4) and PoderNet (1). Source: INE UTSI, Anexo 3 'Terceros que auxiliarán a los OPL', Feb 2024, https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a3.pdf; Morelos: IMPEPAC monthly PREP report, March 2024, p. 19; Campeche: Por Esto, 12 Mar 2024 (press).

### The cost of the problem

On the 52,167 polling stations that were not recounted, INE's two official records of the same paper, the preliminary capture and the certified count, disagree on at least one vote field in 3,382 (6.5%). A difference says two captures disagree, not which one is right; the photo does. On our 300, the photo sided with the certified count on 22 of the 31 it covered. The preliminary count is preliminary by design; the certified count is the official result.

19.2% (26,336 of 137,196) of fully captured national forms fail their own row sum in the official capture. The official capture recorded 28,607 fields as "Ilegible" on 6,009 actas.

Sources: results/national_counts.md (scripts/national_counts.py, PREP 2024 CSV and Cómputos Distritales 2024 CSV); the 300: results/adjudication/CERTIFIED.md; row sums: PREP 2024 CSV, computed in docs/sources/tally-witness-pilot.md §1. Clerical only: no party, no totals, no outcome. Recounts are triggered by legal causes on the paper, not by the PREP, so we claim no recount savings.

### Two 2024 state PREPs, from their own final reports

**Baja California Sur (IEEBCS): a machine first capture is already in a PTO.** Built in-house by the Unidad de
Cómputo y Servicios Informáticos. Final report, *Informe final del PREP, Proceso Electoral Local Ordinario
2023-2024*, <https://www.ieebcs.org.mx/documentos/acuerdos/INFORME_FINAL_PREP_PLE_2023-2024.pdf>:

- p. 6: actas expected / captured: diputaciones locales 1,139 / 1,138; ayuntamientos 1,117 / 1,116; total
  **2,256 / 2,254**. The report gives no total of actas contabilizadas.
- p. 18: "En este proceso electoral se realizó la implementación de lectura automatizada de los datos plasmados en
  las Actas de Escrutinio y Cómputo (AEC) con inteligencia artificial, mediante un Modelo personalizado de la
  herramienta Google Document AI." ... "se tomaron dichos datos como la primera captura, quedando debidamente
  establecido en el Proceso Técnico Operativo (PTO) para este proceso electoral." ... "si dichas capturas eran
  coincidentes, se publicación el AEC, en caso contrario, dicha AEC se asignaba a un tercer capturista o en su
  caso, a módulo de Verificación." *(Automated reading with a custom Google Document AI model was taken as the
  first capture, as set in the PTO; a person made the next capture; if they matched the acta was published,
  otherwise it went to a third capturist or to verification.)*
- p. 19: the automated reading matched the manual capture on **14,501 of 23,077 fields (62.84%)** and on **65 of
  2,254 actas (2.88%)** in full.

So one institute has already written a machine capture into its PTO, under numeral-30-style wording, with people
for the second and third captures. We do not compare our numbers with theirs: different actas, a different
measure (they count agreement with the human capture; we adjudicate disagreements on the paper).

**Morelos (IMPEPAC): a contracted operator.**

- Operator: **Informática Electoral S.C.**, winner of Licitación Pública IMPEPAC/LP/001/2024 "para la
  implementación del Programa de Resultados Electorales Preliminares" (the only remaining bidder; Grupo Proisi
  S.A. de C.V. also took part). IMPEPAC monthly PREP report, March 2024, p. 19,
  <https://impepac.mx/wp-content/uploads/2024/04/Informe_Marzo-2024_PREP.pdf>. The same report's p. 20 says the
  company ran recruitment, selection and training of operating staff. (p. 22 of that report says the company
  "incumplió" the requirements yet was awarded; we read it as a typo and rely on p. 19.) Auditor: Universidad
  Autónoma del Estado de Morelos (p. 19).
- Final report, *Informe Final PREP 23-24*, v2.0, 2 July 2024,
  <https://impepac.mx/wp-content/uploads/2024/07/Informe%20Final%20PREP_23-24_V_2.0.pdf>, pp. 3-4: gubernatura
  2,583 expected, **2,476 captured**, 1,662 contabilizadas; diputaciones 2,624 / **2,525** / 1,705; ayuntamientos
  2,595 / **2,507** / 1,702. p. 47, payment to third parties: the contract under IMPEPAC/LP/001/2024,
  $24,940,000.00 (MXN; the table heading asks for VAT to be included).
- p. 26 describes the verification step as: "el mismo capturista es el encargado de la verificación, confirma que
  los votos registrados sean los mismos que contiene el Acta PREP digitalizada previo a su publicación". *(The
  same capturist does the verification, confirming that the recorded votes are the ones on the digitised Acta PREP
  before publication.)* The report gives no cotejo results and no count of actas corrected.

**Hidalgo (IEEH), extraordinary local election 2024:** "PoderNet S.A. de C.V. empresa en apoyo al diseño,
implementación y operación del PREP" (p. 4), paid $1,914,000.00 by "Asignación por Invitación" (p. 18),
<https://ieehidalgo.org.mx/images/sesiones/2024/Diciembre/Informe_Final_PREP_PELEXT.pdf>.

**Not verified, left out:** the IEEBCS infrastructure supplier (the report names the services, AWS and Fortinet,
not the company); a 2024 PREP operated by Grupo Proisi; any IMPEPAC cotejo or correction counts; a public email
for any IMPEPAC unit.

## 1. The buyer and the trigger

### Channel, now: Mexico's outside audit of every preliminary count

- **The rule.** Reglamento de Elecciones art. 347 says each electoral institute must submit the computer system of
  its preliminary-results programme (PREP) to an audit and designate an outside auditor (numeral 1). Preference
  goes to academic or research institutions, and the auditor is named at least four months before election day
  (numeral 2). Source: the art. 347 citations in IEEH Hidalgo agreement
  [IEEH/CG/022/2024](https://ieehidalgo.org.mx/images/sesiones/2024/Febrero/IEEH-CG-022-2024.pdf), points 9 to 14.
- **The 2027 buyers already exist.** INE's annex "Entes auditores para los Procesos Electorales Locales 2023-2024"
  (February 2024) lists all 32 state institutes. 26 had named an auditor, and every one of the 26 is a university,
  technological institute or research centre (UNAM centres for Aguascalientes, Mexico City, Hidalgo, Puebla,
  Querétaro and Veracruz; Tec de Monterrey campuses for nine states; CINVESTAV, CIMAT, state universities and
  technological institutes for the rest). The other 6 were still choosing.
  [INE annex 5, CCOE session 23-02-2024](https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf).
- **The gap we fill for the auditor.** Art. 347 audits the computer system (black-box functional tests and a
  vulnerability analysis, numeral 1). It does not check the keyed numbers against the paper, field by field. Two
  Hands can do that for the auditor who is already contracted. That field check is our addition to the auditor's
  scope, not a legal requirement; the requirement to capture twice and compare is the institute's own (section 0).
  Status: no buyer contacted yet.
- **The next window.** INE is organising the federal election and **32 concurrent local processes** for 2026-2027
  ([INE Central Electoral, 30 July 2026](https://centralelectoral.ine.mx/2026/07/30/perfila-ine-organizar-el-proceso-electoral-federal-y-32-concurrentes-2026-2027/)).
  Election day is **6 June 2027**, with local deputies elected in 31 states
  ([INE Central Electoral, 31 July 2026](https://centralelectoral.ine.mx/2026/07/31/planeara-y-organizara-ine-mas-de-500-actividades-del-proceso-electoral-federal-2026%E2%80%912027/)).
  Under numeral 2, auditors must be named by early February 2027 at the latest. That is the sales deadline.

### Q&A: why elections?

Most paper records are private, by law or by contract: patient charts, loan files, drug registers, so nobody can publish an error rate on them. Mexico's tally sheets are the clearest exception: the photo, the keyed value and the certified count are all public, so anyone can re-derive every number we report. That is why we measured there. Elections are our proof set, not our only market. Measured so far on presidential tally sheets and UK rainfall ledgers; private records not yet.

### Next markets, not measured

A rule already forces a check of keyed data against paper in each; we have measured none of them.

1. Health facility monthly reports (HMIS / DHIS2): WHO's Data Quality Review recounts the paper source documents against what was keyed into the national database, and DHIS2 is the national health data system in 80+ low- and middle-income countries; the monthly forms carry their own totals (Kenya MOH 711A: new + re-visits = total). Source: WHO, Data Quality Review Module 3 (2020), https://cdn.who.int/media/docs/default-source/data-quality-pages/2021_dqa_module-3_site-assessment-framework.pdf; https://dhis2.org/about/; MOH 711A, https://tciurbanhealth.org/wp-content/uploads/2017/06/M2_-_MOH_711A_Facility_integrated_Form-3.pdf.
2. US mortgage post-closing QC: Fannie Mae's Selling Guide makes lenders re-check at least 10% of the loans they close (or a statistical sample) every month, plus targeted selections, against the source documents; 4.4 million closed-end originations in 2023. Source: Fannie Mae Selling Guide D1-3-01 and D1-3-02 (04/01/2026), https://selling-guide.fanniemae.com/sel/d1-3-01/lender-post-closing-quality-control-review-process; CFPB, https://www.consumerfinance.gov/data-research/hmda/summary-of-2023-data-on-mortgage-lending/.
3. Clinical-trial source data verification: a 7,000-trial analysis found it corrects 1.1% of site-entered data, while monitoring and verification take 15-30% of trial costs; pointing the monitor at the fields the paper disputes is the mechanism we measured on election forms. Source: Medidata/TransCelerate, Clinical Leader Nov 2014, https://www.clinicalleader.com/doc/medidata-transcelerate-biopharma-inc-clinical-trial-0001; Lindblad et al., Clinical Trials 2014; 11: 205-217.

Also: loan files, insurance claims, customs declarations, registries, survey returns; not measured.

### A second line, not the hero: agents that key forms

When an agent keys a form, the paper still has to agree. Receipts work the same for a model as for a person; in our
measurement, Gemma is the agent. Gemma-4-31B-IT keyed every field of the 289 read forms of the pre-registered 300;
alone it mis-keys 173 of 6,358 fields, 1 in 37 (`results/adjudication/SUMMARY.md`), and the same identities that
route a person's slip route the model's: words = digits, rows sum to the total, sections agree. The buyer is anyone
who lets an agent fill a form from paper and must answer for the record. Next market, not measured: we have not sold
or run this for an agent other than our own reader.

## 2. The product and the price

### What the auditor receives

The audit report (`/audit/{id}/report`, built by `app/audit_web.py` and `templates/audit_report.html`):

- the headline "N fields checked, D disputed, each with its photo";
- the method (model digits and words, the paper's own identities);
- every disputed field, with its crop, the keyed value, the model's digits and words, ordered by evidence (strong,
  medium, weak), a "confirmed / not an error" mark and a CSV export.

### What it yields (measured, pre-registered random sample of 300 forms)

| | Value | Source |
|---|---|---|
| Fields checked | 6,358 on 289 read forms | `app/data/headline.json`, `results/adjudication/SUMMARY.md` |
| Fields disputed | 267 (4.2%): **a person checks 1 field in 24 instead of every field** | the same |
| Disputed fields that are capture errors | 52 of 267, **1 in 5** (22 confirmed by the certified count, 30 judged from the photo by the AI adjudicator) | the same |
| Capture error rate at random | at least 52 of 6,358, **1 in 122** | the same |
| Strong-evidence tier | **12 of 18** are capture errors; medium 27 of 80; weak 13 of 169 | sample audit (`POST /api/audit/sample`, `order_check`); rule in `app/capture_audit.py` |
| The model alone | wrong on 173 of 6,358 fields, **1 in 37** | `results/adjudication/SUMMARY.md` |

Read the strong tier first: two of every three are real.

### What one confirmed error costs to find (measured)

Checking the **267 fields the model disputes found 52 capture errors**. Checking 267 fields picked at random would
find **about 2** (267 x 52 / 6,358 = 2.2, at the measured floor of 52 errors in 6,358 fields). In reviewer work:

| | Fields a person looks at per confirmed capture error | Source |
|---|---|---|
| The disputed fields, in any order | **about 5** (267 / 52) | `results/adjudication/SUMMARY.md` |
| The strong-evidence tier first | **1.5** (18 / 12) | sample audit, `app/capture_audit.py` |
| Fields picked at random | **about 122** (6,358 / 52; a floor, so at most 122) | the same |

We found no published, citable time for a person to verify one field against its photo, so we state it in fields,
not minutes.

### The price (proposal, not measured)

All of it from one config value, `app/pricing.py`; `make eval` (`scripts/price_check.py`) fails if a doc says otherwise.

- **Line 1: $1 per form audited (second capture + cotejo + receipts).** Anchored, for scale, on a line for a different step: INE's own line was MXN 9.5M for ~170,000 actas, about MXN 56 (~$3) per acta for a first capture alone (INE CCOE report p. 4; 170,648
  actas expected, PREP 2024 CSV header).
- **Line 2, contingency: $5 per confirmed capture error, $0 if none is found.** Derived once from the measured precision: measured: 52 confirmed capture errors in 267 disputed fields (19.5%, 1 in 5.1) on 289 read forms, 180 per 1,000 forms; $1 / 0.180 = $5.56, rounded down to $5
  (app/data/headline.json; notes/bv-brainstorm/3-model.md section 3 (1 in 5.1 disputed fields confirmed, 180 per 1,000 forms read)). "Confirmed" is defined by a third party: the certified count agrees with the
  paper, or the client's own reviewer marks it on the crop under a receipt.
- Footnote: Self-serve (CLI / MCP, you review your own disputes): $0.10 per form.

### Cost side, honestly

| Per form | Value | Basis |
|---|---|---|
| AMD compute, Gemma-4-31B-IT | $0.00014 | measured: mean $0.000144 over 289 reads, `results/calls_gemma.jsonl` |
| AMD compute, second reader Qwen3.8-27B | $0.00051 | measured, 43 pilot reads, `docs/NUMBERS.md` A2 |
| Review labour for routed fields | $0.09 to $0.13 | **GUESS** on time: 20 s per disputed crop; 267 disputed fields on 289 forms (measured, 0.92 per form); $18 to $25 an hour, in-house US operator (https://www.outsourceaccelerator.com/glossary/data-entry/ ($18 to $25 an hour, in-house US operator)); `notes/bv-brainstorm/3-model.md` section 3 |
| Hosting and sales | not measured | |

Review labour, not compute, is the main cost. At the old $0.10 per form it would have taken the whole price; at $1
it does not.

### What it costs a buyer (examples at line 1)

- Morelos, 7,802 forms: about $7,800 (MXN 143k), under the lowest federal direct-award ceiling. About 9.5% of Morelos's audit line and 0.5% of its PREP cost per acta (MXN 3,409, ~$185) (IMPEPAC Informe Final PREP 23-24, p. 56).
- The largest state (Estado de México), 20,908 forms: about $20,900 (MXN 384k), over the lowest federal direct-award ceiling, under the highest.
- The federal count, 169,005 forms: about $169,000 (MXN 3.1M), over every federal direct-award ceiling: a tender; INE's own line was MXN 9.5M.

The ceilings: Mexico's federal budget for 2026 sets the most a federal agency may award directly, without a tender,
per operation, at **MXN 309,000 to 1,145,000** excluding VAT, according to the
agency's budget (PEF 2026 art. 2 fr. X and Anexo 9, https://dof.gob.mx/2025/SHCP/PEF_2026.html). Those ceilings bind federal agencies; state institutes buy under
state law and their own rules, which we have not checked one by one. Baja California Sur shows a state institute
buying AI reading by direct award (MXN 93,834.49, IEEBCS report p. 31). Presidential sheets per state run from 1,017
(Colima) to 20,908 (Estado de México) (`data/raw/prep/PRES_2024.csv`, `TIPO_ACTA` 2).

For a sense of machine-reading list prices: cloud form extraction lists at $30 per 1,000 pages (Google Document AI
Form Parser, first tier, [pricing](https://cloud.google.com/document-ai/pricing)) and $70 per 1,000 pages (AWS
Textract, tables + forms + queries, [pricing](https://aws.amazon.com/textract/pricing/)). Those products extract; we
sell an audit per form, priced against what the institute already spends per acta.

**Revenue, honestly.** Elections are lumpy: one season every few years, recurring per institute per cycle (32 OPLEs
plus INE). They are the proof market: public, audited, with a named buyer and a deadline. Monthly keyed files (the
next markets above) are next, and not measured.

How big, as arithmetic (ESTIMATE, not counted): about 170,000 federal actas (169,005 presidential sheets in 2024, one per polling station) plus the local actas of the 32 local processes, two to three per polling station where a state elects two or three local offices (Morelos 2024: 7,802 local actas for three offices), so roughly 500,000 to 700,000 actas in a concurrent year; at $1 per acta, under $1M per three-year cycle at list price. Mexico's PREPs are the beachhead; the same field-level check applies wherever keyed values must match paper. (Sources: PREP 2024 CSV (169,005 presidential sheets); IMPEPAC Informe Final PREP 23-24, pp. 3-4 (Morelos local actas); INE Central Electoral 2026-07-30 (32 concurrent local processes). The 2-3 local actas per polling station is our estimate.)

**What it saves, in the buyer's units.** Morelos staffed 110 capture-and-verification posts for 7,802 actas (IMPEPAC
Informe Final PREP 23-24). We found no cited time to key one acta, so we give no hours. The measured share only: the
one-reader gate accepted 18% of forms with no person (measured on presidential forms, not on Morelos's local actas), so
at Morelos's volume about 1,400 actas (0.18 x 7,802) would need no second keying by hand; every other acta still gets
a person, pointed at the disputed fields instead of all 22.

### The same job in other countries (volume only, not measured)

**The referee is arithmetic, and arithmetic has no language. Measured on Spanish handwriting and English ledgers; the only language-specific check is words against digits, and the reader is a multilingual model.**

No second-language corpus with an official keyed record and usable terms was reachable; the language claim stays at what was measured.

Forms of this kind, with rows that sum to a total and often words beside digits, are produced at these volumes every cycle.

**Peru: ONPE's 2026 rule keys every acta twice, one of them by a virtual assistant ("una de ellas, por un asistente virtual"); same process, second country, by regulation; not measured by us.** (ONPE directive, Resolución Jefatural 000093-2026, as reported by El Peruano, 6 Jun 2026, https://elperuano.pe/noticia/297403-onpe-conozca-el-procedimiento-que-se-sigue-durante-el-computo-de-los-votos.)

Every general election produces one handwritten result sheet per polling station, and most are keyed or read by
machine. The count of sheets is the size of the audit:

| Country, election | Polling stations (one result sheet each) | Source |
|---|---|---|
| Mexico, 2024 presidential | 169,005 | PREP 2024 CSV, `data/raw/prep/PRES_2024.csv` |
| Nigeria, 2023 general | 176,846 polling units | [INEC, Polling Units](https://inecnigeria.org/polling-units/) |
| Kenya, 2022 presidential | 46,229 Form 34A | [IEBC press release, 17 Aug 2022](https://www.iebc.or.ke/uploads/resources/qWGJXy8s9t.pdf) ("final tallies of all the 46,229 Form 34A") |
| India, 2024 Lok Sabha | 1,052,664 (10,52,664) | [PIB, ECI data release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2088064&reg=48&lang=2) |
| Peru, 2026 general, first round | 92,766 actas | [El Búho, May 2026](https://elbuho.pe/2026/05/onpe-llega-al-100-del-conteo-de-actas-de-las-elecciones-generales-2026-y-se-ratifica-segunda-vuelta-entre-fujimori-y-sanchez/) |
| Indonesia, 2024 general | 820,161 domestic TPS | [KPU (KIP Bener Meriah repost of KPU RI, 4 Jul 2023)](https://kip-benermeriah.kpu.go.id/blog/read/repost-kpu-ri-dpt-pemilu-2024-nasional-2048-juta-pemilih) |

**A live problem, clerical only.** Indonesia's 2024 count app, Sirekap, read the photographed result sheets by
machine. KPU commissioner Idham Holik attributed input errors to human error and to the system misreading numbers
on the C forms ("angka 3 itu terbaca 8", a 3 read as an 8)
([Antara, 19 Feb 2024](https://gorontalo.antaranews.com/berita/236205/kpu-klaim-salah-input-sirekap-karena-kesalahan-manusia-dan-sistem));
the KPU chair said conversions the system read inaccurately would be corrected
([Antara, 15 Feb 2024](https://www.antaranews.com/berita/3966738/kpu-tegaskan-tak-ada-niat-manipulasi-hasil-suara-di-pemilu-2024)).
That is a result-sheet capture error, the thing we check. We make no claim about any outcome.

## 3. Competitive analysis

"Unknown" means we did not find a vendor statement either way. Cost is list price where the vendor publishes one.

| | Handles handwriting? | Proves each accepted value? | Finds errors in an existing capture? | Photo evidence per finding? | Cost per form | Open model on AMD? |
|---|---|---|---|---|---|---|
| **Two Hands** | yes: digits and words, Spanish, phone photos (measured) | yes: the paper's identities must hold, or a person sees it | **yes, the product** | yes, crop per disputed field | $0.14 per 1,000 compute (measured); $1 per form audited proposed | yes |
| Tesseract | "it won't work very well, as Tesseract is designed for printed text" ([FAQ](https://tesseract-ocr.github.io/tessdoc/FAQ.html)) | no | no (you would build it) | no | free, self-hosted | open source, CPU |
| ABBYY FlexiCapture | yes, ICR for handwritten fields ([page](https://www.abbyy.com/flexicapture/)) | unknown | not a stated feature | unknown | not public | no |
| Rossum | yes, "handwriting in 30 languages" ([page](https://rossum.ai/ai-ocr-software/)) | unknown | not a stated feature | unknown | not public | no |
| Hypatos | unknown | unknown | not a stated feature | unknown | not public | no |
| UiPath Document Understanding | yes, lists handwriting ([docs](https://docs.uipath.com/document-understanding/automation-cloud/latest/user-guide/handwriting-recognition)) | unknown | not a stated feature | unknown | not public | no |
| AWS Textract | yes, but handwriting is English only; returns a confidence score per element ([FAQ](https://aws.amazon.com/textract/faqs/)) | confidence score, not a proof | not a stated feature | no | $1.50 per 1,000 pages text, $70 with forms ([pricing](https://aws.amazon.com/textract/pricing/)) | no |
| Google Document AI | yes, handwriting in Enterprise OCR ([docs](https://cloud.google.com/document-ai/docs/enterprise-document-ocr)) | unknown | not a stated feature | unknown | $1.50 per 1,000 pages OCR, $30 Form Parser ([pricing](https://cloud.google.com/document-ai/pricing)) | no |
| Sampling-based manual audit (status quo) | yes, a person | only for the sampled fields | yes, at the random rate: at least 1 error in 122 fields here | if the auditor files it | not cited | n/a |
| Double keying | yes, people | no: two keyers can agree on a paper that contradicts itself | no, it is a capture | no | not cited | n/a |

**Where we sit next to an IDP platform.** IDP platforms route a share of documents to people; we add the paper's own
arithmetic as a free verifier and a photo for every dispute. Rossum, for example, lists its Starter plan from
**$18,000 per year**, including a "validation screen for exception handling and human in the loop"
([pricing](https://rossum.ai/pricing/)). We found no public per-page price for Rossum, ABBYY Vantage or
Hyperscience, and no public figure from them for the share of documents sent to human review.

Why double keying is not enough: 19.2% of nationally captured tally forms (26,336 of 137,196) fail their own row
sum in the official capture (PREP 2024 CSV, `docs/NUMBERS.md` B). Keying twice copies the paper; it cannot say
which paper is wrong. Any IDP platform above could be configured to compare with a capture. None says it does it,
and none we found shows a crop per finding ordered by the paper's own arithmetic.

## 4. Risks and moats

### Risks

- **Procurement cycles.** Public institutes buy through calls and committees. Auditors are named by early 2027;
  if we miss that, the next window is years away.
- **Political sensitivity.** Election data draws attention. We use clerical language only ("capture error",
  "Option NN"), name no party, and say plainly that the first capture is preliminary and the certified count is
  the official result.
- **Recall is unmeasured.** On the forms the certified count settled by comparison, the model disputed 7 of 7 fields
  where the paper differs from the capture, but only 1 of the 7 is a confirmed capture error (the other 6 are ambiguous
  on the paper; `results/adjudication/RECALL.md`). The multiple between 1 in 5 and 1 in 122 depends on recall.
- **The model alone is wrong on 1 field in 37.** Most disputes are model misreads (156 of 267). That is why the
  model never decides and a person opens each dispute.
- **A model second capture needs the institute's approval.** PTO numeral 33 names a person for the second
  capture; changing that is the governing body's decision (RE art. 339.1 d). Art. 347 audits the system, not the
  field values, so an auditor may also decide the field check is out of scope.
- **Next markets are untested.** We have no health form, loan file or case-report form measured.

### Why it holds

- **The paper's own arithmetic is the judge.** Words must equal digits, rows must sum to the total, sections must
  agree. The model only proposes; a value is accepted when the paper proves it. A competitor needs the same
  per-form-type identities, not a better model.
- **The photo trail.** Every finding has its crop and its mark. An auditor can hand the report to anyone and they can
  check it without trusting us.
- **An open model on AMD.** Gemma-4-31B-IT runs on AMD GPUs. An open model can run on the client's own AMD server so the
  scans never leave the building; we have not run that yet (measured only on the hosted AMD Token Factory). The names-and-signatures column is masked before anything is stored or sent.
- **A form type is a schema file.** The second form type (1850-1960 rainfall ledgers) was configuration, not code.

## 5. Next 90 days

1. **One pilot with a state count's auditor.** Offer the field-level check to one of the academic auditors in the
   INE annex, on that state's 2024 PREP data and scans, free, in exchange for a written evaluation. Target: a signed
   letter before the 2027 auditors are named.
2. **The second form type for elections.** Add a local-election tally sheet schema (local deputies are elected in 31
   states in 2027) and re-run the pre-registered protocol on a fresh random sample.
3. **A self-hosted AMD deployment.** Run Gemma-4-31B-IT on an AMD GPU server we control, measure cost per form
   and throughput without the shared-endpoint pacing, and package it so an auditor can run it inside their own
   network.
