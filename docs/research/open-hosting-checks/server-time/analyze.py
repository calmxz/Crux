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
FREE_CPU_S = 128_571   # reading 1: the CPU part, 4.32 / 0.0000336
FREE_GIB_S = 257_143   # reading 1: the memory part, 0.90 / 0.0000035
LIVE_CAP, STAGING_CAP, DEV_CREDIT = 6.0, 2.0, 10.0  # hosting.md
LEARNERS, OWNER, TESTS_AI = 25.0, 8.0, 20.0         # README.md "Money"
SITTING_WORTH = 0.0084                              # spending.md
DAY_LIMIT = 2 * SITTING_WORTH                       # spending.md: 2 sittings' worth a day
TICKET_SITTINGS = (180, 240)                        # #726's question: "180 to 240 sittings"


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


def past_free_tier(secs, mem_gib):
    """Reading 1: separate CPU and memory allowances; each part bills only past its own allowance."""
    return max(0.0, secs - FREE_CPU_S) * CPU_S + max(0.0, secs * mem_gib - FREE_GIB_S) * GIB_S


def sittings():
    by = collections.defaultdict(list)
    for r in jl(os.path.join(HLOGS, "timed_*.jsonl")):
        by[r["tag"]].append(r)
    out = {}
    for tag, rs in by.items():
        rs.sort(key=lambda r: r["t"])
        cum, cross = 0.0, None
        for r in rs:
            cum += r["cost"]
            if cross is None and cum > DAY_LIMIT:
                cross = r["turn"]
        first = rs[0]["usage"]
        turn_s = collections.defaultdict(float)
        for r in rs:
            turn_s[r["turn"]] += r["call_s"]
        out[tag] = {
            "start": rs[0]["t"], "cost": cum, "cross": cross, "calls": [r["call_s"] for r in rs],
            "first_events": [r["first_event_s"] for r in rs if r.get("first_event_s")],
            "first_write": first["write_1h"] + first["write_5m"], "first_read": first["cache_read"],
            "cache": "warm" if first["cache_read"] > 0 else "cold",
            "heavy": "slice20" in tag, "timed": tag not in VOID_TIME,
            "turns": dict(turn_s), "open_s": sum(turn_s.values()),
        }
    return out


def main():
    S = sittings()
    print("== Haiku 5.5 tutor sittings (timed_*.jsonl), effort medium, 1-hour cache")
    print(f"   a day's limit = 2 x USD {SITTING_WORTH} = USD {DAY_LIMIT:.4f}")
    for tag, s in sorted(S.items(), key=lambda kv: kv[1]["start"]):
        print(f"   {tag}: {s['cache']} cache (first call wrote {s['first_write']}, read {s['first_read']} tokens); "
              f"cost USD {s['cost']:.5f} = {s['cost'] / SITTING_WORTH:.2f} sittings' worth; "
              f"day's limit crossed at reply {s['cross']}"
              + (f"; open {s['open_s']:.1f} s, {s['open_s'] / s['cost']:.0f} s per USD" if s["timed"] else "; time void"))
    groups = collections.OrderedDict()
    for heavy in (False, True):
        for cache in ("cold", "warm"):
            tags = [t for t, s in S.items() if s["heavy"] == heavy and s["cache"] == cache]
            if tags:
                groups[("page-heavy" if heavy else "plain") + ", " + cache] = tags
    print()
    for g, tags in groups.items():
        costs = [S[t]["cost"] for t in tags]
        line = (f"-- {g}: {len(tags)} sittings, cost mean USD {st.mean(costs):.5f} "
                f"(x{st.mean(costs) / SITTING_WORTH:.2f} of USD {SITTING_WORTH})")
        print(line)
    for name, pick in (("plain", lambda s: not s["heavy"]), ("page-heavy, timed", lambda s: s["heavy"] and s["timed"])):
        tags = [t for t, s in S.items() if pick(s) and s["timed"]]
        turns = [v for t in tags for v in S[t]["turns"].values()]
        calls = [v for t in tags for v in S[t]["calls"]]
        firsts = [v for t in tags for v in S[t]["first_events"]]
        opens = [S[t]["open_s"] for t in tags]
        spus = [S[t]["open_s"] / S[t]["cost"] for t in tags]
        print(f"-- {name} ({len(tags)} sittings): turn open median {pct(turns, .5):.1f} s, p90 {pct(turns, .9):.1f} s, "
              f"max {max(turns):.1f} s over {len(turns)} turns; call median {pct(calls, .5):.2f} s over {len(calls)} calls; "
              f"first event median {pct(firsts, .5):.2f} s")
        print(f"   sitting open mean {st.mean(opens):.1f} s (min {min(opens):.1f}, max {max(opens):.1f}); "
              f"s per USD pooled {sum(opens) / sum(S[t]['cost'] for t in tags):.0f}, per sitting {min(spus):.0f} to {max(spus):.0f}")
    plain = [t for t, s in S.items() if not s["heavy"]]
    spu_pooled = sum(S[t]["open_s"] for t in plain) / sum(S[t]["cost"] for t in plain)
    spu_max = max(S[t]["open_s"] / S[t]["cost"] for t in plain)
    plain_open = st.mean([S[t]["open_s"] for t in plain])

    print("\n== Outline reads (outline_*.jsonl), effort low, no cache")
    by = collections.defaultdict(list)
    for r in jl(os.path.join(HLOGS, "outline_*.jsonl")):
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
    read_100 = st.mean([sum(r["cost"] for r in rs) / sum(r["pages"] for r in rs) * 100 for rs in by.values()])
    print(f"   mean USD {read_100:.5f} per 100 pages; open seconds per USD {min(o_spu):.0f} to {max(o_spu):.0f}")

    print("\n== Converter (Gotenberg), wall s / container CPU s / peak MiB")
    allc = list(jl(os.path.join(CLOGS, "bench-*.jsonl")))
    for h in allc:
        if "header" in h:
            print(f"   header: {h['header']}")
    crecs = [r for r in allc if "header" not in r]
    print(f"   source files: " + ", ".join(sorted({f"{r['file']} {r['file_mb']} MB" for r in crecs})))
    print(f"   output PDFs: " + ", ".join(sorted({f"{r['file']} -> {r['pdf_bytes'] / 1e6:.1f} MB, {r['pdf_pages']} pages"
                                                  for r in crecs if r['pdf_bytes']})))
    cell = collections.defaultdict(list)
    for r in crecs:
        cell[(r["cpus"], r["memory"], r["file"])].append(r)
    for (cpus, mem, f), rs in sorted(cell.items()):
        ok = [r for r in rs if r["status"] == 200]
        bad = [r for r in rs if r["status"] != 200]
        line = f"   {cpus} vCPU {mem} {f}: {len(ok)} of {len(rs)} ok"
        if ok:
            line += (f", wall {min(r['wall_s'] for r in ok)}-{max(r['wall_s'] for r in ok)} s, "
                     f"cpu {min(r['cpu_s'] for r in ok)}-{max(r['cpu_s'] for r in ok)} s, "
                     f"peak up to {max(r['mem_peak_mib'] or 0 for r in ok)} MiB")
        if bad:
            line += f"; failed: {', '.join(r['run'] + ' ' + str(r['status']) for r in bad)}"
        print(line)
    two = [r["wall_s"] for r in crecs if r["status"] == 200 and r["cpus"] == "1" and r["memory"] == "2g"]
    conv_wall = max(two)
    print(f"   1 vCPU 2 GiB: wall max {conv_wall} s, median {pct(two, .5):.2f} s over {len(two)} conversions")

    print("\n== Re-cost: Cloud Run, gross, list price, Singapore, no overlap between requests")
    print(f"   plain sittings: {spu_pooled:.0f} s per USD pooled, {spu_max:.0f} s per USD for the highest single sitting")
    for mem in (0.5, 1.0):
        ps = per_second(mem)
        print(f"-- backend 1 vCPU, {mem} GiB: USD {ps:.8f} per open second; live cap USD {LIVE_CAP} = {LIVE_CAP / ps:.0f} s; "
              f"staging cap USD {STAGING_CAP} = {STAGING_CAP / ps:.0f} s")
        for label, usd in (("the learners' USD 25", LEARNERS), ("the learners' and the owner's USD 33", LEARNERS + OWNER)):
            for rate_name, rate in (("pooled", spu_pooled), ("highest sitting", spu_max)):
                secs = usd * rate
                print(f"   all of {label}, {rate_name} {rate:.0f} s/USD: {secs:.0f} s; gross USD {secs * ps:.2f} "
                      f"({'trips' if secs * ps > LIVE_CAP else 'under'} the cap); past the free tier USD "
                      f"{past_free_tier(secs, mem):.2f}, if live had the whole free tier")
        for n in TICKET_SITTINGS:
            secs = n * plain_open
            print(f"   {n} plain sittings: {secs:.0f} s = {secs / FREE_CPU_S:.1%} of the free tier's CPU part; gross USD {secs * ps:.2f}")
        for rate_name, rate in (("pooled", spu_pooled), ("highest sitting", spu_max)):
            print(f"   AI spend through live at which the cap trips, {rate_name}: USD {LIVE_CAP / ps / rate:.2f}")
        print(f"   tests' USD {TESTS_AI:.0f} through staging, pooled: {TESTS_AI * spu_pooled:.0f} s, "
              f"gross USD {TESTS_AI * spu_pooled * ps:.2f} vs staging cap USD {STAGING_CAP}")
    pages_month = 25 * 100 * 31 / 7
    files = pages_month / 100
    ps2 = per_second(2.0)
    for scale in (1, 2):
        per_file = (conv_wall * scale + 10) * ps2
        print(f"-- converter at 2 GiB, longest laptop time x{scale} + 10 s shutdown: USD {per_file:.5f} per 100-page file; "
              f"{files:.0f} files a month (25 x 100 pages x 31/7 weeks) = USD {per_file * files:.2f}; "
              f"with every read overrunning USD {2 * per_file * files:.2f}")

    print("\n== Re-cost: the AI month for one learner at every limit (31-day month)")
    weeks = 31 / 7
    tutoring = 17 * SITTING_WORTH  # spending.md: at most about 17 sittings' worth a month
    # Per problem, maths to worded, Haiku writing and marking with Opus's independent check:
    # claude-anthropic-api-check.md (#802 research)
    per_problem = (0.0042, 0.0090)
    for g, tags in groups.items():
        m = st.mean([S[t]["cost"] for t in tags])
        print(f"   17 sittings' worth (USD {tutoring:.3f}) buys {tutoring / m:.1f} sittings of the {g} kind")
    for n in (2, 6, 10):
        lo, hi = n * per_problem[0], n * per_problem[1]
        print(f"   checks of {n} problems: USD {lo:.4f} (maths) to {hi:.4f} (worded) each; 2 a week = {2 * weeks:.2f} "
              f"a month = USD {2 * weeks * lo:.3f} to {2 * weeks * hi:.3f}")
    reading = weeks * read_100
    print(f"   reading 100 pages a week = USD {reading:.3f} a month; with the overrun (up to 199 pages a week) "
          f"USD {reading * 1.99:.3f}")
    for n in (6, 10):
        worst = tutoring + 2 * weeks * n * per_problem[1] + reading * 1.99
        print(f"   one learner at every limit, {n}-problem worded checks, every read overrunning: USD {worst:.3f}; "
              f"x25 = USD {25 * worst:.2f} vs the learners' USD 25")


if __name__ == "__main__":
    main()
