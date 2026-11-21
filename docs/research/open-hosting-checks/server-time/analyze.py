"""#726 item 5: every figure in server-time.md, computed from the raw logs in this folder.

Usage: python analyze.py > analysis-<date>.txt
ASCII-only output. Re-run after new runs; the write-up quotes this script's output.
"""
import collections
import glob
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
HLOGS = os.path.join(HERE, "haiku", "logs")
CLOGS = os.path.join(HERE, "converter", "logs")

# Tags whose times are void: their topic slice was split without pruning, so every turn
# uploaded about 40 MB (see haiku/logs/superseded-unpruned-pdf). Their costs stand.
VOID_TIME = {"v3_haiku_medium_A3_slice20", "v3_haiku_medium_B3_slice20"}

# Prices and allowances, from cloud-run-billing.md (Singapore, Tier 2, request-based).
CPU_S = 0.0000336      # USD per vCPU-second
GIB_S = 0.0000035      # USD per GiB-second
FREE_S = 128_571       # free instance-seconds at 1 vCPU (reading 1: CPU part, 4.32 / 0.0000336)
LIVE_CAP, STAGING_CAP, DEV_CREDIT = 6.0, 2.0, 10.0  # hosting.md
AI_LIVE = {"learners": 25.0, "owner's share": 8.0}  # README.md "Money"
TESTS_AI = 20.0
SITTING_WORTH = 0.0084  # spending.md


def pct(a, p):
    a = sorted(a)
    i = (len(a) - 1) * p
    lo = int(i)
    hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (i - lo)


def jl(pattern):
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                yield json.loads(line)


def per_second(mem_gib):
    return CPU_S + mem_gib * GIB_S


def main():
    print("== Haiku 5.5 tutor turns (timed_*.jsonl), effort medium, 1-hour cache")
    recs = list(jl(os.path.join(HLOGS, "timed_*.jsonl")))
    turn_s = collections.defaultdict(float)
    cost = collections.defaultdict(float)
    for r in recs:
        cost[r["tag"]] += r["cost"]
        if r["tag"] not in VOID_TIME:
            turn_s[(r["tag"], r["turn"])] += r["call_s"]
    groups = {"plain": [t for t in cost if "slice" not in t],
              "slice20": [t for t in cost if "slice20" in t]}
    s_per_usd = {}
    for g, tags in groups.items():
        timed = [t for t in tags if t not in VOID_TIME]
        turns = [v for (t, _), v in turn_s.items() if t in timed]
        sit_s = [sum(v for (t, _), v in turn_s.items() if t == tag) for tag in timed]
        costs = [cost[t] for t in tags]
        print(f"-- {g}: sittings costed {len(tags)}, timed {len(timed)}")
        for t in sorted(tags):
            ts = sum(v for (x, _), v in turn_s.items() if x == t)
            print(f"   {t}: tutor cost USD {cost[t]:.5f}" + ("" if t in VOID_TIME else f", open {ts:.1f} s"))
        print(f"   cost per sitting: mean USD {st.mean(costs):.5f} (min {min(costs):.5f}, max {max(costs):.5f}); "
              f"vs spending.md USD {SITTING_WORTH}: x{st.mean(costs) / SITTING_WORTH:.2f}")
        if turns:
            print(f"   turn open time: n {len(turns)}, median {pct(turns, .5):.1f} s, p90 {pct(turns, .9):.1f} s, "
                  f"max {max(turns):.1f} s")
            print(f"   sitting open time: mean {st.mean(sit_s):.1f} s (min {min(sit_s):.1f}, max {max(sit_s):.1f})")
            spu = sum(sit_s) / sum(cost[t] for t in timed)
            s_per_usd[g] = spu
            print(f"   open seconds per USD of tutoring: {spu:.0f}")
    calls = [r["call_s"] for r in recs if r["tag"] not in VOID_TIME]
    firsts = [r["first_event_s"] for r in recs if r["tag"] not in VOID_TIME and r.get("first_event_s")]
    print(f"   calls {len(calls)}: median {pct(calls, .5):.2f} s, p90 {pct(calls, .9):.2f} s; "
          f"first stream event median {pct(firsts, .5):.2f} s")

    print("\n== Outline reads (outline_*.jsonl), effort low, no cache")
    orecs = list(jl(os.path.join(HLOGS, "outline_*.jsonl")))
    by = collections.defaultdict(list)
    for r in orecs:
        by[r["tag"]].append(r)
    o_spu = []
    for tag, rs in sorted(by.items()):
        secs = sum(r["call_s"] for r in rs)
        c = sum(r["cost"] for r in rs)
        pages = sum(r["pages"] for r in rs)
        o_spu.append(secs / c)
        parts = ", ".join(f"{r['first_page']}-{r['last_page']} ({r['counted_input']} tok, {r['call_s']:.1f} s, "
                          f"out {r['usage']['output_tokens']})" for r in rs)
        print(f"   {tag}: {pages} pages in {len(rs)} parts [{parts}]; {secs:.1f} s, USD {c:.5f}, "
              f"USD {c / pages * 100:.5f} per 100 pages, {secs / c:.0f} s per USD")
    if o_spu:
        print(f"   open seconds per USD of reading: {min(o_spu):.0f} to {max(o_spu):.0f}")

    print("\n== Converter (Gotenberg), wall s / container CPU s / peak MiB")
    crecs = [r for r in jl(os.path.join(CLOGS, "bench-*.jsonl")) if "header" not in r]
    for h in jl(os.path.join(CLOGS, "bench-*.jsonl")):
        if "header" in h:
            print(f"   header: {h['header']}")
    cell = collections.defaultdict(list)
    for r in crecs:
        cell[(r["cpus"], r["memory"], r["file"])].append(r)
    for (cpus, mem, f), rs in sorted(cell.items()):
        ok = [r for r in rs if r["status"] == 200]
        bad = [r for r in rs if r["status"] != 200]
        line = f"   {cpus} vCPU {mem} {f}: {len(ok)} ok"
        if ok:
            line += (f", wall {min(r['wall_s'] for r in ok)}-{max(r['wall_s'] for r in ok)} s, "
                     f"cpu {min(r['cpu_s'] for r in ok)}-{max(r['cpu_s'] for r in ok)} s, "
                     f"peak up to {max(r['mem_peak_mib'] or 0 for r in ok)} MiB")
        if bad:
            line += f"; {len(bad)} failed ({', '.join(r['run'] + ' ' + str(r['status']) for r in bad)})"
        print(line)
    two = [r["wall_s"] for r in crecs if r["status"] == 200 and r["cpus"] == "1" and r["memory"] == "2g"]
    conv_wall = max(two)
    print(f"   1 vCPU 2 GiB: wall max {conv_wall} s, median {pct(two, .5):.2f} s over {len(two)} conversions")

    print("\n== Re-cost: Cloud Run, gross, list price, Singapore")
    spu_max = max(s_per_usd.values())
    for mem in (0.5, 1.0):
        ps = per_second(mem)
        print(f"-- backend 1 vCPU, {mem} GiB: USD {ps:.8f} per open second; free tier {FREE_S} s; "
              f"live cap USD {LIVE_CAP} = {LIVE_CAP / ps:.0f} s; staging cap USD {STAGING_CAP} = {STAGING_CAP / ps:.0f} s")
        for label, usd in [("learners only", AI_LIVE["learners"]), ("learners + owner's share", sum(AI_LIVE.values()))]:
            secs = usd * spu_max
            gross = secs * ps
            net = max(0.0, (secs - FREE_S)) * ps
            print(f"   all of {label} (USD {usd:.0f}) at {spu_max:.0f} s/USD, no overlap: {secs:.0f} s, "
                  f"gross USD {gross:.2f} (cap {'TRIPS' if gross > LIVE_CAP else 'holds'}), "
                  f"after free tier USD {net:.2f} (Developer credit USD {DEV_CREDIT:.0f} "
                  f"{'covers' if net <= DEV_CREDIT else 'does not cover'})")
        for n in (180, 240):
            secs = n * st.mean([sum(v for (t, _), v in turn_s.items() if t == tag) for tag in groups["plain"]])
            print(f"   {n} plain sittings: {secs:.0f} s, gross USD {secs * ps:.2f}")
        trip = LIVE_CAP / ps / spu_max
        print(f"   AI spend through live at which the cap trips (no overlap): USD {trip:.2f}")
        print(f"   tests' USD {TESTS_AI:.0f}, if it all ran through staging: {TESTS_AI * spu_max:.0f} s, "
              f"gross USD {TESTS_AI * spu_max * ps:.2f} vs staging cap USD {STAGING_CAP}")
    print("\n== Re-cost: the AI month for one learner at every limit (31-day month)")
    weeks = 31 / 7
    tutoring = 17 * SITTING_WORTH  # spending.md: at most about 17 sittings' worth a month
    # Per problem, Haiku writing and marking with Opus's independent check: claude-anthropic-api-check.md (#802 research)
    per_problem = (0.0042, 0.0090)
    read_100 = st.mean([sum(r["cost"] for r in rs) / sum(r["pages"] for r in rs) * 100 for rs in by.values()])
    plain_mean = st.mean([cost[t] for t in groups["plain"]])
    heavy_mean = st.mean([cost[t] for t in groups["slice20"]])
    print(f"   tutoring: 17 x USD {SITTING_WORTH} = USD {tutoring:.3f} (money, so fixed); buys {tutoring / plain_mean:.1f} "
          f"plain sittings at USD {plain_mean:.5f}, or {tutoring / heavy_mean:.1f} page-heavy at USD {heavy_mean:.5f}")
    day = 2 * SITTING_WORTH
    print(f"   a day's limit (2 x {SITTING_WORTH} = USD {day:.4f}) is {day / heavy_mean:.0%} of one page-heavy sitting "
          f"(about {15 * day / heavy_mean:.0f} of its 15 replies), and {day / (2 * plain_mean):.0%} of two plain sittings")
    for n in (2, 6, 10):
        lo, hi = n * per_problem[0], n * per_problem[1]
        print(f"   checks of {n} problems: USD {lo:.4f} to {hi:.4f} each; 2 a week = {2 * weeks:.2f} a month = "
              f"USD {2 * weeks * lo:.3f} to {2 * weeks * hi:.3f}")
    reading = 100 * weeks / 100 * read_100
    print(f"   reading: USD {read_100:.5f} per 100 pages; 100 pages a week = USD {reading:.3f} a month; with the "
          f"overrun (a file starting at page 99 read in full, up to 199 pages a week) up to USD {reading * 1.99:.3f}")
    for n in (6, 10):
        worst = tutoring + 2 * weeks * n * per_problem[1] + reading * 1.99
        print(f"   one learner at every limit, {n}-problem checks at the high end, with overruns: USD {worst:.3f}; "
              f"x25 learners = USD {25 * worst:.2f} vs the learners' USD 25")

    pages_month = 25 * 100 * 31 / 7
    files = pages_month / 100
    ps2 = per_second(2.0)
    for scale in (1, 2):
        per_file = (conv_wall * scale + 10) * ps2
        print(f"-- converter at 2 GiB, laptop time x{scale} + 10 s shutdown per file: USD {per_file:.5f} per 100-page file; "
              f"{files:.0f} files a month (25 learners x 100 pages x 31/7 weeks) = USD {per_file * files:.2f}, "
              f"twice that with overruns USD {2 * per_file * files:.2f}")


if __name__ == "__main__":
    main()
