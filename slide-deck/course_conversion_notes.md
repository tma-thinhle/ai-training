# Course conversion notes

## Source and completion

- Source: `TMA_AI_Engineering_Fast_Track_Member_Package_v12_Self_Learning_Ready.pptx`.
- Actual presentation count: **51 slides**, confirmed from the presentation slide-ID list, slide extraction and 51 rendered PDF pages.
- The cover is slide 1; the closing “READY TO BUILD?” slide is slide 51. The source visibly numbers slides 2–50. Both unnumbered slides are included.
- Output: `course_slides.md`, with exactly one `Slide N — Original title` section for every slide, in presentation order.
- No missing or duplicated slide numbers. No remaining slide range.
- No beginner explanations, external course material or assignment solutions were added.
- Source SHA-256: `10bcbf0d3beada9168d050382ae64900cc1839c9450ae4b2acaf89ada6c76568`.

## Saved batch progress

| Batch | Slides saved | Final status |
| --- | --- | --- |
| 1 | 1–10 | Transcribed, saved, then verified |
| 2 | 11–20 | Transcribed, saved, then verified |
| 3 | 21–30 | Transcribed, saved, then verified |
| 4 | 31–40 | Transcribed, saved, then verified |
| 5 | 41–51 | Transcribed, saved, then verified |

Both deliverables were written during batch processing. This final notes file replaces the provisional batch-status notes after verification.

## Verification actually performed

- Compared every nonempty text shape with its corresponding Markdown slide section: **1,327 text-bearing shapes accounted for**, including 82 bullet-only shapes represented as Markdown bullets.
- Independently reopened the original PPTX ZIP/XML and followed the presentation relationship order. Checked all **1,336 nonempty text runs** against the corresponding Markdown sections, normalizing only Markdown escapes, line wrapping and whitespace. Result: **zero missing text runs**.
- Tracked every text-bearing shape during conversion; every shape was consumed exactly once. Repeated source instructions remain repeated on the corresponding slides.
- Rendered all 51 slides to PDF. Independently compared per-slide alphanumeric token counts from the source text with PDF text: no source-token deficits on any slide. This check supplements the exact source-to-Markdown text check; it does not prove pixel-identical rendering.
- Inspected rendered contact sheets covering all 51 slides for titles, layout, card/table grouping, reading order and visible images. Also inspected individual slide renders for setup commands, feature mapping and assessment protocol, and the embedded logo at its original size.
- Checked the weekly requirement/pass-criteria pairs on slides 22, 24, 26, 28, 30, 32, 34 and 36, their implementation guides on slides 23–37, and gates/scoring/datasets/submission/tracking on slides 39–50 against the source text. Numeric thresholds, dates, weights, case counts, commands, endpoint/function names and placeholders are retained.
- Checked all **46 hyperlink occurrences** against the original XML relationships: **31 external occurrences** covering **16 distinct URLs**, plus **15 internal slide jumps**. The five contents-row backgrounds duplicate the five section-title links; that relationship is stated separately on slide 2. All five “↑ CONTENTS” links return to slide 2.
- Checked for speaker-note parts: **zero**. Checked for embedded chart, diagram-data and embedded-object parts: none. Diagram/flow content on the slides is built from ordinary shapes and text.
- Checked diagram labels and arrows on slide 12 and the four-milestone layout on slide 6. Transcribed labels remain source text; added spatial descriptions are clearly labeled. The empty checkboxes on slide 46 are also identified separately.

## Conversion conventions

- Original wording, capitalization, punctuation and meaningful line breaks are retained. Markdown escapes protect literal underscores, brackets, vertical bars and comparison signs; `<br>` represents source line breaks within cells or text shapes.
- Titles were identified from the visible headings because the source does not use PowerPoint title placeholders. Slide 1 joins the two visible title lines, “AI ENGINEERING” and “FAST-TRACK,” into one heading. Section-divider headings use the large visible section title.
- Multi-column cards are read by coherent card or row, from left to right and then downward; text inside each card remains together. The footer moves to the end of its slide section.
- Tables drawn as individual text boxes and shapes are reconstructed as Markdown tables. There are no native PowerPoint table objects in the deck. Added column labels only identify the structure of those cards/rows.
- Bullet shapes become Markdown bullets; numbered implementation steps preserve their original numbers. Empty text boxes, decorative backgrounds, lines and accents are omitted. No substantive course text is omitted.
- The source has no standalone code blocks. Its shell commands, API paths, function names, schema/model names and file paths are preserved as text; no code was invented or executed.
- The image-based “TMA innovation” logo wording is transcribed separately on slides 1 and 51. The course content is otherwise available as editable slide text.
- Speaker-note status is shown separately for every slide. Absence of note parts is reported as absence, rather than as a successful transcription of unseen notes.

## Limitations and unresolved items — retained flags

| Flag | Slides affected | Checked against source | Not verified / limitation |
| --- | --- | --- | --- |
| U1 — External link availability | 14, 15, 22, 24, 26, 28, 30, 32, 34, 36 | All hyperlink labels and embedded URL destinations were checked against the PPTX. | Websites were not opened. Current availability, redirects, changed course titles/content and access requirements remain unverified. Source URLs are preserved exactly. |
| U2 — Companion repository unavailable | 18–19, 23–37, 46–50 | Filenames, paths, suggested module layouts, commands, expected results and submission fields were checked against the slides. | Only the PPTX was attached. The starter ZIP/repository, fixtures, actual API/model access, cost cap, hidden tests and staging environment were not supplied. File existence, actual fixture counts and expected test outcomes cannot be confirmed. Suggested paths were not reconciled with an unseen repository. |
| U3 — No embedded speaker notes | 1–51 | The source archive contains no speaker-note parts. | No speaker notes can be transcribed. Notes from earlier versions or external presenter material cannot be assessed. |
| U4 — Visual fidelity boundary | 1–51 | Text, visible grouping and slide order were checked using the source XML and rendered slides. | Markdown preserves content and reading order, not original typography, coordinates, colors, animations or click-region geometry. The visual rendering was produced by LibreOffice rather than native Microsoft PowerPoint. |

**Unreadable or ambiguous transcription:** No unreadable substantive course text or unresolved text-reading ambiguity was found. The flags above remain open; successful transcription does not verify the external materials they describe. Source scope wording, suggested filenames and acceptance criteria are retained without editorial reconciliation.

## Slide-by-slide coverage checklist

Each checked row means: heading and text accounted for; original XML text compared with Markdown; rendered slide visually inspected; source/PDF alphanumeric text cross-check passed. “Notes absent” means no source speaker-note part exists. Link counts include duplicate click regions when present. U1–U4 refer to the retained limitations above.

| Covered | Slide | Original title | XML text runs checked | Hyperlinks checked | Notes | Flags / specific visual coverage |
| --- | --- | --- | --- | --- | --- | --- |
| [x] | 1 | AI ENGINEERING FAST-TRACK | 8 | 0 | Notes absent | U3, U4; logo text |
| [x] | 2 | How to Navigate This Package | 31 | 10 | Notes absent | U3, U4; navigation rows |
| [x] | 3 | PROGRAM GUIDE | 16 | 1 | Notes absent | U3, U4 |
| [x] | 4 | Program overview | 20 | 0 | Notes absent | U3, U4 |
| [x] | 5 | How members should follow the program | 21 | 0 | Notes absent | U3, U4 |
| [x] | 6 | Your 8-Week Journey | 47 | 0 | Notes absent | U3, U4; milestone layout |
| [x] | 7 | Your Weekly Targets & Expected Outcomes | 44 | 0 | Notes absent | U3, U4; weekly target table |
| [x] | 8 | Weekly operating cadence | 23 | 0 | Notes absent | U3, U4 |
| [x] | 9 | PROJECT & LAB SETUP | 16 | 1 | Notes absent | U3, U4 |
| [x] | 10 | WHY  \|  Your mission & project goal | 22 | 0 | Notes absent | U3, U4 |
| [x] | 11 | WHAT  \|  Functional scope & expected outputs | 21 | 0 | Notes absent | U3, U4 |
| [x] | 12 | HOW  \|  Technical architecture & stack | 26 | 0 | Notes absent | U3, U4; architecture arrows/service boxes |
| [x] | 13 | Your MVP Definition of Done | 16 | 0 | Notes absent | U3, U4 |
| [x] | 14 | Course library  \|  Weeks 1–4 | 28 | 8 | Notes absent | U1, U3, U4; course link cards |
| [x] | 15 | Course library  \|  Weeks 5–8 | 28 | 8 | Notes absent | U1, U3, U4; course link cards |
| [x] | 16 | Weekly Learning Checklist  \|  W1–W4 | 26 | 0 | Notes absent | U3, U4 |
| [x] | 17 | Weekly Learning Checklist  \|  W5–W8 | 26 | 0 | Notes absent | U3, U4 |
| [x] | 18 | Before Week 1  \|  Developer Setup | 21 | 0 | Notes absent | U2, U3, U4; setup commands |
| [x] | 19 | Resources  \|  Where Everything Lives | 24 | 0 | Notes absent | U2, U3, U4; resource paths/counts |
| [x] | 20 | WEEKLY BUILD TRACK | 16 | 1 | Notes absent | U3, U4 |
| [x] | 21 | BUILD  \|  Connecting weekly labs to the final product | 43 | 0 | Notes absent | U3, U4; feature mapping table |
| [x] | 22 | W1  \|  Prompt engineering & issue classification | 29 | 2 | Notes absent | U1, U3, U4 |
| [x] | 23 | W1  \|  How to build: issue classification | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 24 | W2  \|  LLM API & structured responses | 29 | 2 | Notes absent | U2, U1, U3, U4 |
| [x] | 25 | W2  \|  How to build: meeting notes API | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 26 | W3  \|  Embeddings & semantic search | 29 | 2 | Notes absent | U2, U1, U3, U4 |
| [x] | 27 | W3  \|  How to build: semantic document search | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 28 | W4  \|  Grounded RAG knowledge assistant | 29 | 2 | Notes absent | U2, U1, U3, U4 |
| [x] | 29 | W4  \|  How to build: grounded knowledge Q&A | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 30 | W5  \|  Tool calling & Jira analysis agent | 29 | 2 | Notes absent | U2, U1, U3, U4 |
| [x] | 31 | W5  \|  How to build: Jira analysis agent | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 32 | W6  \|  Multi-step agent workflow & approval | 29 | 2 | Notes absent | U2, U1, U3, U4 |
| [x] | 33 | W6  \|  How to build: reporting workflow + review | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 34 | W7  \|  LLMOps, security & staging deployment | 29 | 2 | Notes absent | U2, U1, U3, U4 |
| [x] | 35 | W7  \|  How to build: production hardening | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 36 | W8  \|  Final capstone & individual challenge | 28 | 1 | Notes absent | U2, U1, U3, U4 |
| [x] | 37 | W8  \|  How to build: final demo and readiness | 31 | 0 | Notes absent | U2, U3, U4 |
| [x] | 38 | ASSESSMENT & GATES | 16 | 1 | Notes absent | U3, U4 |
| [x] | 39 | Four checkpoints  \|  strict pass / fail | 21 | 0 | Notes absent | U3, U4 |
| [x] | 40 | Assignment scoring rubric  \|  100 points | 20 | 0 | Notes absent | U3, U4; rubric |
| [x] | 41 | Overall readiness score | 31 | 0 | Notes absent | U3, U4; weights/classification |
| [x] | 42 | Shared synthetic dataset & evaluation design | 23 | 0 | Notes absent | U3, U4; benchmark counts |
| [x] | 43 | Negative testing  \|  cases that must not fail | 22 | 0 | Notes absent | U3, U4 |
| [x] | 44 | Assessment Protocol  \|  No Ambiguity | 18 | 0 | Notes absent | U3, U4; gate protocol |
| [x] | 45 | SUBMISSION & TRACKING | 16 | 1 | Notes absent | U3, U4 |
| [x] | 46 | Weekly submission checklist | 17 | 0 | Notes absent | U2, U3, U4; empty checkboxes |
| [x] | 47 | Final demo script  \|  20 minutes per team | 20 | 0 | Notes absent | U2, U3, U4; demo sequence/timing |
| [x] | 48 | Weekly tracker  \|  fill during Friday review | 68 | 0 | Notes absent | U2, U3, U4; tracker table/placeholders |
| [x] | 49 | Individual assessment scorecard | 24 | 0 | Notes absent | U2, U3, U4; scorecard/checkboxes |
| [x] | 50 | Member action list  \|  start on Monday | 33 | 0 | Notes absent | U2, U3, U4 |
| [x] | 51 | READY TO BUILD? | 5 | 0 | Notes absent | U3, U4; logo text/closing slide |

## External destination inventory — source-verified only

This inventory records the exact distinct destinations stored in the PPTX; it is not a web-availability check (U1). Each occurrence remains linked in its own slide section.

| Destination copied from source | Slide occurrences |
| --- | --- |
| [https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/](https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/) | 14, 22 |
| [https://learn.deeplearning.ai/courses/chatgpt-prompt-eng/](https://learn.deeplearning.ai/courses/chatgpt-prompt-eng/) | 14, 22 |
| [https://developers.openai.com/api/docs/quickstart](https://developers.openai.com/api/docs/quickstart) | 14, 24 |
| [https://developers.openai.com/api/docs/guides/structured-outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | 14, 24 |
| [https://www.deeplearning.ai/courses/vector-databases-embeddings-applications](https://www.deeplearning.ai/courses/vector-databases-embeddings-applications) | 14, 26 |
| [https://developers.openai.com/api/docs/guides/retrieval](https://developers.openai.com/api/docs/guides/retrieval) | 14, 26 |
| [https://learn.microsoft.com/en-us/azure/search/resource-training](https://learn.microsoft.com/en-us/azure/search/resource-training) | 14, 28 |
| [https://www.deeplearning.ai/alpha/short-courses/building-evaluating-advanced-rag](https://www.deeplearning.ai/alpha/short-courses/building-evaluating-advanced-rag) | 14, 28 |
| [https://huggingface.co/learn/agents-course/en/unit1/introduction](https://huggingface.co/learn/agents-course/en/unit1/introduction) | 15, 30 |
| [https://openai.github.io/openai-agents-python/quickstart/](https://openai.github.io/openai-agents-python/quickstart/) | 15, 30 |
| [https://developers.openai.com/api/docs/guides/function-calling](https://developers.openai.com/api/docs/guides/function-calling) | 15, 32 |
| [https://py.sdk.modelcontextprotocol.io/get-started/](https://py.sdk.modelcontextprotocol.io/get-started/) | 15, 32 |
| [https://genai.owasp.org/llm-top-10/](https://genai.owasp.org/llm-top-10/) | 15, 34 |
| [https://learn.microsoft.com/en-us/training/paths/operationalize-gen-ai-apps/](https://learn.microsoft.com/en-us/training/paths/operationalize-gen-ai-apps/) | 15, 34 |
| [https://developers.openai.com/api/docs/guides/evaluation-best-practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | 15, 36 |
| [https://academy.langchain.com/courses/langgraph-essentials-python](https://academy.langchain.com/courses/langgraph-essentials-python) | 15 |

## Internal destination inventory

| Source slide / control | Actual target in presentation order |
| --- | --- |
| 2 / PROGRAM GUIDE title and row background | Slide 3 |
| 2 / PROJECT & LAB SETUP title and row background | Slide 9 |
| 2 / WEEKLY BUILD TRACK title and row background | Slide 20 |
| 2 / ASSESSMENT & GATES title and row background | Slide 38 |
| 2 / SUBMISSION & TRACKING title and row background | Slide 45 |
| 3, 9, 20, 38, 45 / ↑ CONTENTS | Slide 2 |

**Final status:** All 51 slides completed and verified to the extent stated above. No remaining slides; no unresolved transcription omissions. U1–U4 are retained.
