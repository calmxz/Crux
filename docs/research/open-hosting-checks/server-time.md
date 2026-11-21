# Item 5: server time per sitting and per upload (#726)

Question: does Cloud Run's free tier still cover live, tests, staging and file work, now that the trial converts and reads every upload? And what do a page-heavy sitting and a file read cost against the learners' money?

The method follows two later inputs on the ticket:

- **From #802:** measure Haiku 5.5 at `medium`, not Flash-Lite. Time an outline read in parts under 100,000 tokens, at `low`. Re-cost with a sitting's worth of USD 0.0084, 2 checks and 100 pages a week, and the learners' USD 25.
- **From the owner, 2026-11-20:** convert two generated worst-case files in place of real decks.

Every run was on **2026-11-21**. The measured figures come from two logs:

- [`server-time/analysis-2026-11-21.txt`](server-time/analysis-2026-11-21.txt), the output of [`server-time/analyze.py`](server-time/analyze.py). Rerun the script to recompute it from the raw logs.
- [`haiku/logs/split-check-2026-11-21.txt`](server-time/haiku/logs/split-check-2026-11-21.txt), for page-split sizes, token counts and the machine.

Prices and the free tier come from [`cloud-run-billing.md`](cloud-run-billing.md).

## Short answer

| Question | Answer |
|---|---|
| How long a tutor turn holds the request open | Median 4.2 s, 90th percentile 6.6 s, longest 15.4 s, over 90 turns. A 15-reply sitting holds it about 68 s in all. |
| What a plain sitting costs | USD 0.00927 when the instructions are not yet cached, USD 0.00820 when they are. The spec's USD 0.0084 sits between. |
| Page-heavy sitting (a 20-page topic slice) | The first sitting on a file pays to cache its pages: USD 0.0233, or 2.77 sittings' worth. A day's limit ends at reply 9 or 10 of 15. |
| Outline read of a 100-page file | 2 parts, 14 to 22 s, about USD 0.018. |
| Converter, 100-page worst-case files | 6 to 10 s at 1 vCPU. 1 GiB fails on a later conversion in the same instance. 2 GiB held 12 in a row, but its high-water mark reached the full 2 GiB. |
| Does the free tier hold? | At 180 to 240 sittings a month, yes: 9.5% to 12.7% of its CPU part. At full use of the learners' USD 25, no. |
| Does the live cap hold? | Not at full use. The USD 6 gross cap trips at about USD 19 to 22 of AI spend through live in a month. |
| Does the AI month fit USD 25 at every limit? | With 6-problem checks, yes: USD 19.49 for 25 learners. With 10-problem worded checks, no: USD 27.46. |

## How each time was measured

Cloud Run bills an instance for every second that at least one request is open, in 100 ms steps [cloud-run-billing.md, C3]. A streamed reply keeps its request open until the last byte. So the figure that matters is wall-clock time with the request open, not CPU used.

- **Tutor turns.** [`timed_sitting.py`](server-time/haiku/scripts/timed_sitting.py) reruns the #802 teaching harness, copied unchanged apart from how `common.py` finds the key, with each tutor call streamed and timed. A turn can take several calls, because tool calls report results and the tutor then carries on. A turn's time is the sum of its calls.
- **Outline reads.** [`outline_read.py`](server-time/haiku/scripts/outline_read.py) fits each part to the most pages under 95,000 counted tokens, then streams the call at `low` with no cache. Its instruction is a research stand-in, not Crux's prompt.
- **Converter.** [`gotenberg_bench.py`](server-time/converter/gotenberg_bench.py) runs Gotenberg in Docker, limited to a chosen number of vCPUs and memory. Each size gets a fresh container: one cold conversion, then two warm ones.
- **The files.** [`make_worst_case_files.py`](server-time/converter/make_worst_case_files.py) builds a 100-slide PowerPoint file (30.6 MB) and a 100-page Word file (30.2 MB). 80 of every 100 pages carry a full-size photo, and the rest hold charts, tables, equations and mixed layouts. Word charts are images, since python-docx cannot write native charts.

## 1. Tutor turns on Haiku 5.5 at `medium`

Six plain sittings, three personas run twice, 15 learner replies each, with the 1-hour cache. The first three ran with nothing cached. The next three started within the hour, so their first call read the 5,800-token instructions from the cache.

| Sitting | Cache at the start | Teaching cost | Request open |
|---|---|---|---|
| C1 | cold | USD 0.00983 | 77.7 s |
| A1 | cold | USD 0.00983 | 80.7 s |
| B1 | cold | USD 0.00815 | 71.0 s |
| A2 | warm | USD 0.00785 | 58.3 s |
| B2 | warm | USD 0.00747 | 54.3 s |
| C2 | warm | USD 0.00929 | 65.2 s |

- **Cost:** cold sittings average USD 0.00927, 1.10 times the spec's USD 0.0084. Warm sittings average USD 0.00820, 0.98 times it.
- The spec's figure came from 6 sittings at a 5-minute cache, times 1.1 [`spending.md`]. In Crux, the instructions are shared by every learner, so they stay warm while anyone has used Crux in the last hour. This is a reading, not a measurement.
- **Time:** a turn's median is 4.2 s, its 90th percentile 6.6 s, and its longest 15.4 s. A sitting holds requests open 54.3 to 80.7 s, 67.9 s on average.
- A single call's median is 2.35 s, over 138 calls. The first streamed event arrives after a median of 1.05 s.
- **Seconds per dollar:** the six sittings held requests open 7,770 s per USD of teaching, pooled. Single sittings ranged from 7,023 to 8,715 s per USD.

## 2. A page-heavy topic

Here, the first learner message carried a 20-page topic slice from a converted worst-case file. 20 pages is the spec's limit of added pages [`files.md`]. 20 pages count as 34,823 tokens from the deck and 33,989 from the Word file [split-check].

| Sitting | Slice from | Cache at the start | Teaching cost | Day's limit ends at | Request open |
|---|---|---|---|---|---|
| A3 | the deck | cold | USD 0.02291 | reply 10 | void, see below |
| B3 | the Word file | cold | USD 0.02365 | reply 9 | void, see below |
| A4 | the deck | warm: read A3's slice | USD 0.01579 | not reached | 111.2 s |
| B4 | the Word file | warm: read B3's slice | USD 0.01655 | not reached | 113.6 s |

- **The first sitting on a file is the cold case.** Its first call wrote about 40,000 tokens to the cache. A learner's slice is their own, so nobody else warms it. This is a reading of the spec, not a measurement.
- Cold: USD 0.0233 on average, 2.77 sittings' worth. A day's limit is 2 sittings' worth, USD 0.0168 [`spending.md`]. The two cold runs crossed it at replies 10 and 9.
- Warm: USD 0.0162, 1.92 sittings' worth. That case is a second sitting on the same topic within the hour. Neither warm run reached a day's limit.
- A month's 17 sittings' worth, USD 0.143, buys about 6.1 cold page-heavy sittings, against 15.4 cold plain ones.
- **Times:** A3 and B3 split their slice in a way that sent about 40 MB with every turn (see [A gotcha in splitting pages](#a-gotcha-in-splitting-pages)). So their times are void.
- A3 and B3's costs stand. The same pages count the same tokens either way [split-check].
- A4 and B4's turns had a median of 8.2 s and a 90th percentile of 9.7 s, over 30 turns. They held requests open 6,950 s per USD.

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

Gotenberg 8.40.0 (`gotenberg/gotenberg@sha256:53073e79...`). It ran on the owner's computer: an AMD Ryzen 9 8945HS, with Docker 29.8.2 on WSL 2 and cgroup v1 [split-check].

| Size | File | Converted | Wall time | Peak memory |
|---|---|---|---|---|
| 1 vCPU, 2 GiB | Deck | 6 of 6 | 7.14 to 10.09 s | 1,432 MiB |
| 1 vCPU, 2 GiB | Word file | 6 of 6 | 6.08 to 7.52 s | 1,646 MiB |
| 1 vCPU, 1 GiB | Deck | 2 of 4 | 8.67 to 8.88 s | 1,024 MiB |
| 1 vCPU, 1 GiB | Word file | 4 of 6 | 6.08 to 7.47 s | 1,024 MiB |
| 2 vCPU, 2 GiB | Deck | 6 of 6 | 7.24 to 9.01 s | 1,703 MiB |
| 2 vCPU, 2 GiB | Word file | 6 of 6 | 5.65 to 7.57 s | 1,042 MiB |

- **1 GiB fails on a later conversion in the same instance.** It failed on the deck's second conversion and on the Word file's third, in both passes.
- In each failure, the container hit its memory limit and Gotenberg answered 500: "LibreOffice failed to convert the document". The first conversion in a fresh container passed.
- **2 GiB held** every conversion, peaking at 1.0 to 1.7 GiB over 3 conversions per container.
- **Twelve in a row.** [`long_run.py`](server-time/converter/long_run.py) then ran 12 conversions of each file in one 1 vCPU, 2 GiB container ([`long-run-12.txt`](server-time/converter/logs/long-run-12.txt)). All 24 converted.
  - Current memory climbed for 3 conversions, then held at about 1.35 GiB on the deck and 1.2 to 1.4 GiB on the Word file.
  - It fell to 0.17 to 0.33 GiB at the 10th conversion. Gotenberg restarts LibreOffice after 10 conversions by default (`--libreoffice-restart-after`, "default 10", from the image's `--help`).
  - The high-water mark reached the full 2,048 MiB: at the deck's 10th conversion and the Word file's 7th. Nothing was killed.
  - Under cgroup v1, that mark includes reclaimable file cache. So how much headroom 2 GiB leaves is not shown.
  - Reading: on Cloud Run, files written inside the container also use memory, so the 30 MB upload and its PDF add to the total there.
- **A second vCPU did not help.** Wall time stayed about the same, and the CPU-seconds used stayed close to the wall time.
- **No timeout.** Every conversion finished well inside Gotenberg's default request timeout. A second pass with a 600 s timeout gave the same results.
- **The machine is fast.** A Cloud Run vCPU may be slower than this laptop's cores, so the re-cost below also doubles these times.

## A gotcha in splitting pages

The spec says "Crux splits the pages from the PDF" for the topic slice [`files.md`]. On these Gotenberg PDFs, every page points to one resource list holding every image in the file.

- A plain `pypdf` page copy carries that whole list. One page of the deck came out at 40,829,320 base64 characters, the size of the whole file [split-check].
- Pruning each page to the images its content names fixes it, but only before `add_page`. Pruning after the copy changes nothing, since the copy has already brought every image along.
- The pruned split gives 548,784 base64 characters for one page of the deck, and 20,559,088 for 50 [split-check]. See [`pdf_parts.py`](server-time/haiku/scripts/pdf_parts.py).
- The token count is the same either way. The cost is upload size and time: about 40 MB with every turn.

## 5. Re-cost: Cloud Run against the free tier and the caps

**Prices.** Singapore is Tier 2. A request-based instance at 1 vCPU costs USD 0.00003535 a second at 512 MiB, and USD 0.0000371 at 1 GiB, at list price [cloud-run-billing.md, C1].

**The free tier** has a CPU part and a memory part. Under the note's reading 1, the CPU part covers 128,571 vCPU-seconds and the memory part 257,143 GiB-seconds in Singapore [cloud-run-billing.md, C2]. Every project on the billing account shares it. The spend cap counts gross use, before the free tier (item 2).

**The model.** The spec does not set the backend's memory, so both sizes follow. The re-cost counts every AI dollar at the teaching rate, assuming no two requests overlap.

- Overlapping requests on one instance bill once, so overlap can only lower these figures.
- The pooled rate is 7,770 s per USD. The highest single sitting reached 8,715 s per USD, so the range uses both.
- Reads hold far fewer seconds per dollar (785 to 1,194). A check's time was not measured.

| Month | Open seconds | Gross, 512 MiB | Gross, 1 GiB | Against the USD 6 live cap |
|---|---|---|---|---|
| 180 plain sittings (the ticket's figure) | 12,219 s | USD 0.43 | USD 0.45 | Holds |
| 240 plain sittings (the ticket's figure) | 16,292 s | USD 0.58 | USD 0.60 | Holds |
| All of the learners' USD 25 | 194,260 to 217,884 s | USD 6.87 to 7.70 | USD 7.21 to 8.08 | Trips |
| The learners' USD 25 and the owner's USD 8 | 256,423 to 287,607 s | USD 9.06 to 10.17 | USD 9.51 to 10.67 | Trips |

- **The free tier:** at full use, the backend alone passes the free tier's CPU part.
- If live had the whole free tier, the learners' USD 25 would leave USD 2.21 to 3.00 to pay. With the owner's USD 8 as well, it would leave USD 4.30 to 5.45.
- Staging, the tasks service and the converter share the free tier, so the real amount left is higher.
- The owner's USD 10 Developer Program credit may pay what is left [`hosting.md`].
- **The live cap trips first.** It counts gross use. At 512 MiB it trips at USD 19.47 to 21.84 of AI spend through live; at 1 GiB, at USD 18.56 to 20.81.
- When it trips, Google pauses every Cloud Run service in the project [`hosting.md`].
- **Staging:** at the pooled rate, all of the tests' USD 20 through staging would be 155,408 s, or USD 5.49 to 5.77 gross. That would trip staging's USD 2 cap. This note does not settle whether AI tests run through staging's Cloud Run or call Anthropic from CI.
- **The converter is small.** At 2 GiB, a 100-page worst-case file costs USD 0.00082 gross, counting the longest laptop time plus 10 s of shutdown. Doubling the conversion time gives USD 0.00123.
- 25 learners reading 100 pages a week is about 111 such files a month: USD 0.09 to 0.14. With every read overrunning, it is USD 0.18 to 0.27.
- Conversion is not under the reading limit [`spending.md`], so uploads past it add more, at about a tenth of a cent each.
- **Not counted:** the backend's own work between model calls, the tasks service waiting on the converter, and instance start-up time.

## 6. Re-cost: the AI month at every limit

One learner who uses every limit in a 31-day month (31 / 7 = 4.43 weeks):

| Part | Rule | Cost |
|---|---|---|
| Teaching | 17 sittings' worth x USD 0.0084 [`spending.md`] | USD 0.143 |
| Checks of 6 problems | 2 a week = 8.86 a month, USD 0.0252 (maths) to 0.0540 (worded) each | USD 0.223 to 0.478 |
| Checks of 10 problems | the same, USD 0.0420 to 0.0900 each | USD 0.372 to 0.797 |
| Reading | 100 pages a week, USD 0.018 per 100 pages | USD 0.080 |
| Reading with overruns | up to 199 pages a week | up to USD 0.159 |

- A check's cost per problem is USD 0.0042 for maths to USD 0.0090 for worded problems, from the #802 research. That counts Haiku writing and marking, plus Opus's independent check.
- **With 6-problem worded checks and every read overrunning:** USD 0.780 a learner, or USD 19.49 for 25 learners. That fits the learners' USD 25.
- **With 10-problem worded checks and every read overrunning:** USD 1.099 a learner, or USD 27.46 for 25. That passes USD 25.
- Guests' USD 2 a month spends from the same budget [`trial.md`].
- At the budget, the month's limit and the daily ceiling stop new spending. A started check still runs past every limit [`spending.md`], so the month can end a little over USD 25.

## What this means for recorded decisions

This note reports facts. Each choice below belongs to the owner.

| Finding | Recorded decision it touches |
|---|---|
| At full use of the learners' budget, the USD 6 gross live cap trips | #716's caps, #675's hosting costs, the map's constraints line |
| The converter needs 2 GiB; 1 GiB fails on a later conversion | #716's converter, "1 to 2 GiB" in `hosting.md` |
| The first sitting on a 20-page slice costs 2.77 sittings' worth, so a day's limit ends at reply 9 or 10 | #675's tutoring limit, #802's sitting's worth |
| A plain sitting costs USD 0.00927 cold and USD 0.00820 warm, around the spec's USD 0.0084 | #802's sitting's worth, in `spending.md`'s Gaps |
| At every limit with 10-problem worded checks, the month passes USD 25 | #802's re-cost, #675's limits |
| Splitting a Gotenberg PDF page by page carries every image into each part | A build check for the topic slice and the outline read |

## Not measured

- **Where the calls start.** The times were measured from the owner's computer, not from Singapore. Network time to Anthropic from Cloud Run may differ.
- **Cloud Run's CPU speed** against this laptop's. The doubled converter figure is a guess, not a measurement.
- **A check's time.** Opus costs more per token than Haiku, so its calls probably add fewer seconds per dollar. This is a reading.
- **Real decks.** The owner's method change adds one public lecture deck only if the month comes close to the credit. At the ticket's 180 to 240 sittings it is well inside, so the deck was not added. The full-use case is bound by money, not by deck weight.

## Files

- [`server-time/converter/`](server-time/converter/): the file builder, the benchmark and its logs. The generated files are not committed; rebuild them with the builder.
- [`server-time/haiku/scripts/`](server-time/haiku/scripts/): the #802 harness, copied unchanged apart from how `common.py` finds the key, plus `timed_sitting.py`, `outline_read.py`, `pdf_parts.py` and `split_check.py`. They load the key named in `common.py` from the main checkout's `.env`, and never print it.
- [`server-time/haiku/logs/`](server-time/haiku/logs/): one JSON line per model call, with its usage, cost and time. `superseded-unpruned-pdf/` holds the console output of the runs with the oversized split.
- The sittings' full transcripts are kept locally, not committed. No figure comes from them.
- The runs cost USD 0.24 in all, by the logs' list-price count, simulated learner included.
