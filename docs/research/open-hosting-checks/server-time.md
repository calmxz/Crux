# Item 5: server time per sitting and per upload (#726)

Question: does Cloud Run's free tier still cover live, tests, staging and file work, now that the trial converts and reads every upload? And what do a page-heavy sitting and a file read cost against the learners' money?

The method follows two later inputs on the ticket:

- **From #802:** measure Haiku 5.5 at `medium`, not Flash-Lite. Time an outline read in parts under 100,000 tokens, at `low`. Re-cost with a sitting's worth of USD 0.0084, 2 checks and 100 pages a week, and the learners' USD 25.
- **From the owner, 2026-11-20:** convert two generated worst-case files in place of real decks.

Every run was on **2026-11-21**. Every figure below comes from [`server-time/analysis-2026-11-21.txt`](server-time/analysis-2026-11-21.txt). Rerun [`server-time/analyze.py`](server-time/analyze.py) to recompute it from the raw logs. Prices and the free tier come from [`cloud-run-billing.md`](cloud-run-billing.md).

## Short answer

| Question | Answer |
|---|---|
| How long a tutor turn holds the request open | Median 4.2 s, 90th percentile 6.6 s, longest 15.4 s, over 90 turns. A 15-reply sitting holds it about 68 s in all. |
| Page-heavy sitting (a 20-page topic slice) | About USD 0.020 and 112 s. That is 2.35 sittings' worth, so a day's limit ends about 13 replies into one such sitting. |
| Outline read of a 100-page file | 2 parts, 14 to 22 s, about USD 0.018. |
| Converter, 100-page worst-case files | 6 to 10 s at 1 vCPU. 1 GiB fails on a second file in the same instance; 2 GiB holds, peaking at 1.7 GiB. |
| Does the free tier hold? | At 180 to 240 sittings a month, easily: 12,000 to 16,000 s of its 128,571 s. At full use of the learners' USD 25, no. |
| Does the live cap hold? | Not at full use. The USD 6 gross cap trips once about USD 21 of AI spend has run through live in a month. |
| Does the AI month fit USD 25 at every limit? | With 6-problem checks, yes: USD 19.49 for 25 learners. With 10-problem checks at the high end, no: USD 27.46. |

## How each time was measured

Cloud Run bills an instance for every second that at least one request is open, in 100 ms steps [cloud-run-billing.md, C3]. A streamed reply keeps its request open until the last byte. So the figure that matters is wall-clock time with the request open, not CPU used.

- **Tutor turns.** [`timed_sitting.py`](server-time/haiku/scripts/timed_sitting.py) reruns the #802 teaching harness, copied unchanged, with each tutor call streamed and timed. A turn can take several calls, because tool calls report results and the tutor then carries on. A turn's time is the sum of its calls.
- **Outline reads.** [`outline_read.py`](server-time/haiku/scripts/outline_read.py) fits each part to the most pages under 95,000 counted tokens, then streams the call at `low` with no cache. Its instruction is a research stand-in, not Crux's prompt.
- **Converter.** [`gotenberg_bench.py`](server-time/converter/gotenberg_bench.py) runs Gotenberg in Docker, limited to a chosen number of vCPUs and memory. Each size gets a fresh container: one cold conversion, then two warm ones.
- **The files.** [`make_worst_case_files.py`](server-time/converter/make_worst_case_files.py) builds a 100-slide PowerPoint file and a 100-page Word file, about 30 MB each. 80 of every 100 pages carry a full-size photo, and the rest hold charts, tables, equations and mixed layouts. Word charts are images, since python-docx cannot write native charts.

## 1. Tutor turns on Haiku 5.5 at `medium`

Six plain sittings, three personas run twice, 15 learner replies each, with the 1-hour cache:

| Sitting | Teaching cost | Request open |
|---|---|---|
| A1 | USD 0.00983 | 80.7 s |
| A2 | USD 0.00785 | 58.3 s |
| B1 | USD 0.00815 | 71.0 s |
| B2 | USD 0.00747 | 54.3 s |
| C1 | USD 0.00983 | 77.7 s |
| C2 | USD 0.00929 | 65.2 s |
| **Mean** | **USD 0.00874** | **67.9 s** |

- A turn's median is 4.2 s, its 90th percentile 6.6 s, and its longest 15.4 s.
- A single call's median is 3.06 s. The first streamed event arrives after a median of 1.13 s.
- Late turns run a little longer than early ones, as the history grows.
- **Seconds per dollar:** the six sittings held requests open 7,770 s per USD of teaching.
- **The sitting's worth:** the mean, USD 0.00874, is 1.04 times the spec's USD 0.0084. That estimate came from 6 sittings at a 5-minute cache, times 1.1 [`spending.md`]. This is the first measurement at the 1-hour cache.
- The first three sittings alone averaged USD 0.0093. The next three brought the mean down, so the sample is still small.

## 2. A page-heavy topic

Here, the first learner message carried a 20-page topic slice from a converted worst-case file. 20 pages is the spec's limit of added pages [`files.md`]. 20 of these photo-heavy pages count as 34,823 tokens.

| Sitting | Slice from | Teaching cost | Request open |
|---|---|---|---|
| A3 | the deck | USD 0.02291 | void, see below |
| B3 | the Word file | USD 0.02365 | void, see below |
| A4 | the deck | USD 0.01579 | 111.2 s |
| B4 | the Word file | USD 0.01655 | 113.6 s |
| **Mean** | | **USD 0.01972** | **112.4 s** |

- A3 and B3 split their slice in a way that sent about 40 MB with every turn (see [A gotcha in splitting pages](#a-gotcha-in-splitting-pages)). Their times are void.
- Their costs stand. The same pages count the same tokens either way: 1,726 for one page and 34,823 for 20, split both ways.
- A turn's median is 8.2 s and its 90th percentile 9.7 s, over the 30 turns of A4 and B4.
- A4 and B4 held requests open 6,950 s per USD of teaching, fewer than plain sittings.
- **Against the limits:** a page-heavy sitting costs 2.35 sittings' worth.
- A day's limit is 2 sittings' worth, USD 0.0168 [`spending.md`]. That is 85% of one page-heavy sitting, so it ends about 13 of its 15 replies in.
- A month's 17 sittings' worth, USD 0.143, buys about 7.2 page-heavy sittings, or 16.3 plain ones.

## 3. Reading a file into its outline

Each worst-case PDF was read twice, at `low`, with no cache:

| Read | Parts (pages, counted tokens) | Time | Cost |
|---|---|---|---|
| Word file, run 1 | 1-55 (93,585), 56-100 (76,836) | 20.3 s | USD 0.01799 |
| Word file, run 2 | 1-55 (93,585), 56-100 (76,837) | 13.8 s | USD 0.01755 |
| Deck, run 1 | 1-54 (94,248), 55-100 (80,398) | 18.2 s | USD 0.01800 |
| Deck, run 2 | 1-54 (94,248), 55-100 (80,385) | 22.0 s | USD 0.01846 |

- A 100-page file takes 2 parts under 95,000 tokens each.
- A read costs about USD 0.018 per 100 pages, nearly all of it input.
- It holds a request open 785 to 1,194 s per USD, far fewer seconds per dollar than teaching.
- **Overrun:** a file whose read starts within the week's 100 pages is read in full [`spending.md`]. At worst, a 100-page file starts at page 99, so a week reads 199 pages. That costs about USD 0.036 for one learner.
- The outlines were poor, since the generated pages repeat 10 topic names. Outline quality is not this item's question.

## 4. The converter

Gotenberg 8.40.0 (`gotenberg/gotenberg@sha256:53073e79...`), on the owner's computer: an AMD Ryzen 9 8945HS, Docker on WSL 2 with cgroup v1.

| Size | File | Converted | Wall time | Peak memory |
|---|---|---|---|---|
| 1 vCPU, 2 GiB | Deck | 6 of 6 | 7.14 to 10.09 s | 1,432 MiB |
| 1 vCPU, 2 GiB | Word file | 6 of 6 | 6.08 to 7.52 s | 1,646 MiB |
| 1 vCPU, 1 GiB | Deck | 2 of 4 | 8.67 to 8.88 s | 1,024 MiB |
| 1 vCPU, 1 GiB | Word file | 4 of 6 | 6.08 to 7.47 s | 1,024 MiB |
| 2 vCPU, 2 GiB | Deck | 6 of 6 | 7.24 to 9.01 s | 1,703 MiB |
| 2 vCPU, 2 GiB | Word file | 6 of 6 | 5.65 to 7.57 s | 1,042 MiB |

- **1 GiB fails on a later conversion.** It failed on the deck's first warm conversion and on the Word file's second, in both passes.
- In each failure, the container hit its memory limit and Gotenberg answered 500: "LibreOffice failed to convert the document". The first conversion in a fresh container passed.
- **2 GiB held** every conversion, peaking at 1.4 to 1.7 GiB.
- **A second vCPU did not help.** Wall time was about the same, and the CPU-seconds used stayed close to the wall time.
- **No timeout.** Every conversion finished well inside Gotenberg's default request timeout. A second pass with a 600 s timeout gave the same results.
- CPU-seconds used track wall time closely: 7.11 to 9.77 s for the deck at 1 vCPU, 2 GiB.
- **The machine is fast.** A Cloud Run vCPU may be slower than this laptop's cores, so the re-cost below also doubles these times.

## A gotcha in splitting pages

The spec says "Crux splits the pages from the PDF" for the topic slice [`files.md`]. On these Gotenberg PDFs, every page points to one resource list holding every image in the file.

- A plain `pypdf` page copy carries that whole list. One page came out at 40.8 MB of base64, the size of the whole file.
- Pruning each page to the images its content names fixes it, but only before `add_page`. Pruning after the copy changes nothing, since the copy has already brought every image along.
- The fixed split gives 0.4 MB for one page and 15.4 MB for 50 pages of the deck. See [`pdf_parts.py`](server-time/haiku/scripts/pdf_parts.py).
- The token count is the same either way. The cost is upload size and time: a 40 MB request with every turn.

## 5. Re-cost: Cloud Run against the free tier and the caps

Prices: Singapore is Tier 2. A request-based instance at 1 vCPU costs USD 0.00003535 a second at 512 MiB and USD 0.0000371 at 1 GiB, at list price [cloud-run-billing.md, C1]. The free tier covers 128,571 s at 1 vCPU, under the lower reading [cloud-run-billing.md, C2]. The spend cap counts gross use, before the free tier (item 2).

The backend's memory is not set in the spec, so both sizes follow. The upper bound counts every AI dollar at the teaching rate of 7,770 s per USD. That is the most seconds per dollar measured. Reads (785 to 1,194 s per USD) and Opus's independent check cost more per second, so they add fewer seconds per dollar. It assumes no two requests overlap; overlapping requests on one instance bill once, so real use can only be lower.

| Month | Open seconds | Gross, 512 MiB | Gross, 1 GiB | Against the USD 6 live cap |
|---|---|---|---|---|
| 180 plain sittings | 12,219 s | USD 0.43 | USD 0.45 | Holds |
| 240 plain sittings | 16,292 s | USD 0.58 | USD 0.60 | Holds |
| All of the learners' USD 25 | 194,260 s | USD 6.87 | USD 7.21 | Trips |
| The learners' USD 25 and the owner's USD 8 | 256,423 s | USD 9.06 | USD 9.51 | Trips |

- **The free tier:** at full use, the backend alone passes the free tier's 128,571 s.
- What is left after the free tier is USD 2.32 to 4.74 a month. The owner's USD 10 Developer Program credit would cover it, if it pays Cloud Run [`hosting.md`].
- **The live cap trips first.** It counts gross use, so it trips once about USD 21 of AI spend has run through live: USD 21.84 at 512 MiB, USD 20.81 at 1 GiB.
- When it trips, Google pauses every Cloud Run service in the project [`hosting.md`].
- **Staging:** if all of the tests' USD 20 ran through staging, that would be 155,408 s, or USD 5.49 to 5.77 gross. That would trip staging's USD 2 cap.
- Whether AI tests run through staging's Cloud Run, or call Anthropic from CI, is not settled in this note.
- **The converter is small.** At 2 GiB, a 100-page worst-case file costs USD 0.00082 gross, counting the laptop's longest time plus 10 s of shutdown. Doubling the conversion time gives USD 0.00123.
- 25 learners reading 100 pages a week is about 111 such files a month: USD 0.09 to 0.14, or USD 0.18 to 0.27 with every read overrunning.
- Conversion is not under the reading limit [`spending.md`], so uploads past the reading limit add more. Each file is still under a tenth of a cent.
- **Not counted:** the backend's own work between model calls, the tasks service waiting on the converter, and instance start-up time.

## 6. Re-cost: the AI month at every limit

One learner who uses every limit in a 31-day month (31 / 7 = 4.43 weeks):

| Part | Rule | Cost |
|---|---|---|
| Teaching | 17 sittings' worth x USD 0.0084 [`spending.md`] | USD 0.143 |
| Checks of 6 problems | 2 a week = 8.86 a month, USD 0.0252 to 0.0540 each | USD 0.223 to 0.478 |
| Checks of 10 problems | the same, USD 0.0420 to 0.0900 each | USD 0.372 to 0.797 |
| Reading | 100 pages a week, USD 0.018 per 100 pages | USD 0.080 |
| Reading with overruns | up to 199 pages a week | up to USD 0.159 |

- A check's cost per problem is USD 0.0042 to 0.0090 from the #802 research. That counts Haiku writing and marking, plus Opus's independent check.
- **With 6-problem checks at the high end and every overrun:** USD 0.780 a learner, or USD 19.49 for 25 learners. That fits the learners' USD 25.
- **With 10-problem checks at the high end and every overrun:** USD 1.099 a learner, or USD 27.46 for 25. That passes USD 25.
- Guests' USD 2 a month spends from the same budget [`trial.md`].
- In that case the month's budget and the daily ceiling stop Crux as the spec already says. No new rule is needed for the money to stay inside USD 25.

## What this means for recorded decisions

This note reports facts. Each choice below belongs to the owner.

| Finding | Recorded decision it touches |
|---|---|
| At full use of the learners' budget, the USD 6 gross live cap trips | #716's caps, #675's hosting costs, the map's constraints line |
| The converter needs 2 GiB; 1 GiB fails on a later file | #716's converter, "1 to 2 GiB" in `hosting.md` |
| A page-heavy sitting costs 2.35 sittings' worth, so a day's limit ends partway through one | #675's tutoring limit, #802's sitting's worth |
| The measured plain sitting is USD 0.00874, 4% over the spec's USD 0.0084 | #802's sitting's worth, in `spending.md`'s Gaps |
| At every limit with 10-problem checks, the month passes USD 25 | #802's re-cost, #675's limits |
| Splitting a Gotenberg PDF naively carries every image into each part | A build check for the topic slice and the outline read |

## Not measured

- **Where the calls start.** The times were measured from the owner's computer, not from Singapore. Network time to Anthropic from Cloud Run may differ.
- **Cloud Run's CPU speed** against this laptop's. The doubled figure is a guess, not a measurement.
- **A check's time.** Its seconds are bounded by its dollars at the teaching rate, which is the upper bound used above.
- **Real decks.** The owner's method change adds one public lecture deck only if the month comes close to the credit. At typical use it is well inside, so it was not added. The full-use case is bound by money, not by deck weight.

## Files

- [`server-time/converter/`](server-time/converter/): the file builder, the benchmark and its logs. The generated files are not committed; rebuild them with the builder.
- [`server-time/haiku/scripts/`](server-time/haiku/scripts/): the #802 harness, copied unchanged, plus `timed_sitting.py`, `outline_read.py` and `pdf_parts.py`. They load the key named in `common.py` from the main checkout's `.env`, and never print it.
- [`server-time/haiku/logs/`](server-time/haiku/logs/): one JSON line per model call, with its usage, cost and time. `superseded-unpruned-pdf/` holds the console output of the runs with the oversized split.
- The sittings' full transcripts are kept locally, not committed. No figure comes from them.
- The runs cost USD 0.24 in all, by the logs' list-price count, simulated learner included.
