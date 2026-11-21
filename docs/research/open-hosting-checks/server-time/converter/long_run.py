"""#726 item 5 follow-up: many conversions in one converter instance.

The first benchmark ran 3 conversions per container. This runs N in one container at
1 vCPU and 2 GiB, and after each records the container's current memory as well as its
high-water mark (the high-water mark can only rise within a container).

Usage: python long_run.py <files_dir> <log_path> [n]
ASCII-only output.
"""
import json
import sys
import time
from pathlib import Path

import gotenberg_bench as gb

# gotenberg_bench reads its image and timeout from its own argv slots at import time;
# this script's argv differs, so set both explicitly.
gb.IMAGE = "gotenberg/gotenberg:8"
gb.API_TIMEOUT = None


def mem_now():
    for p in ("memory.current", "memory/memory.usage_in_bytes"):
        try:
            return int(gb.cg(p))
        except Exception:
            continue
    return None


def main(files_dir, log_path, n=12):
    files_dir, log = Path(files_dir), Path(log_path)
    with open(log, "a", encoding="utf-8") as out:
        out.write(json.dumps({"header": {"image": gb.IMAGE, "n": n, "size": "1 vCPU 2g",
                                         "started": time.strftime("%Y-%m-%d %H:%M:%S")}}) + "\n")
        for f in gb.FILES:
            gb.start("1", "2g")
            for i in range(1, n + 1):
                rec = gb.convert(files_dir / f)
                now, peak = mem_now(), gb.mem_peak()
                rec.update({"file": f, "conversion": i,
                            "mem_now_mib": None if now is None else round(now / 2**20, 1),
                            "mem_peak_mib": None if peak is None else round(peak / 2**20, 1)})
                out.write(json.dumps(rec) + "\n")
                out.flush()
                print(f"{f} #{i}: status {rec['status']} wall {rec['wall_s']} s now {rec['mem_now_mib']} MiB "
                      f"peak {rec['mem_peak_mib']} MiB {rec['state_oomkilled_running']}")
            gb.sh("docker", "rm", "-f", gb.NAME, check=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12)
