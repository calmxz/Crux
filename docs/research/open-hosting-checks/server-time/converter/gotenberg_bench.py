"""Converter benchmark for #726 item 5: Gotenberg (LibreOffice) on the two worst-case files.

For each container size (vCPUs, memory) and each file:
- cold: a fresh container, LibreOffice not yet started, one conversion;
- warm: two more conversions in the same container.
Records wall-clock seconds for the HTTP call, container CPU-seconds used (cgroup v2
cpu.stat usage_usec), the container's peak memory (memory.peak), the HTTP status,
and the PDF's page count and size. Wall time at the container's size is what Cloud
Run's request-based billing charges for; CPU-seconds are reported for reference.

Usage: python gotenberg_bench.py <files_dir> <log_path> [image] [api_timeout]
Needs: Docker, requests, pypdf. ASCII-only output.
"""
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import requests
from pypdf import PdfReader

IMAGE = sys.argv[3] if len(sys.argv) > 3 else "gotenberg/gotenberg:8"
API_TIMEOUT = sys.argv[4] if len(sys.argv) > 4 else None  # None = Gotenberg's default
SIZES = [("1", "2g"), ("1", "1g"), ("2", "2g")]
FILES = ["worst-case-100-slides.pptx", "worst-case-100-pages.docx"]
WARM_RUNS = 2
PORT = 3726
NAME = "crux-726-gotenberg"


def sh(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check).stdout.strip()


def cg(path):
    return sh("docker", "exec", NAME, "cat", f"/sys/fs/cgroup/{path}")


def cpu_usec():
    """Container CPU time in microseconds: cgroup v2 cpu.stat, else cgroup v1 cpuacct.usage (ns)."""
    try:
        for line in cg("cpu.stat").splitlines():
            k, v = line.split()
            if k == "usage_usec":
                return int(v)
    except subprocess.CalledProcessError:
        pass
    return int(cg("cpuacct/cpuacct.usage")) // 1000


def mem_peak():
    """Container peak memory in bytes: cgroup v2 memory.peak, else v1 memory.max_usage_in_bytes."""
    for p in ("memory.peak", "memory/memory.max_usage_in_bytes"):
        try:
            return int(cg(p))
        except subprocess.CalledProcessError:
            continue
    return None


def start(cpus, mem):
    sh("docker", "rm", "-f", NAME, check=False)
    cmd = ["docker", "run", "-d", "--name", NAME, f"--cpus={cpus}", f"--memory={mem}", f"--memory-swap={mem}",
           "-p", f"{PORT}:3000", IMAGE, "gotenberg"]
    if API_TIMEOUT:
        cmd.append(f"--api-timeout={API_TIMEOUT}")
    sh(*cmd)
    t0 = time.time()
    while time.time() - t0 < 120:
        try:
            if requests.get(f"http://localhost:{PORT}/health", timeout=2).status_code == 200:
                return time.time() - t0
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("gotenberg did not become healthy")


def convert(path):
    c0, t0 = cpu_usec(), time.perf_counter()
    status, pages, size, err = None, None, None, None
    try:
        with open(path, "rb") as fh:
            r = requests.post(f"http://localhost:{PORT}/forms/libreoffice/convert",
                              files={"files": (path.name, fh)}, timeout=900)
        status = r.status_code
        if status == 200:
            size = len(r.content)
            pages = len(PdfReader(io.BytesIO(r.content)).pages)
            pdf = path.with_suffix(path.suffix + ".pdf")  # kept for the outline-read test
            if not pdf.exists():
                pdf.write_bytes(r.content)
        else:
            err = r.text[:300]
    except requests.RequestException as e:
        err = repr(e)[:300]
    wall = time.perf_counter() - t0
    oom = sh("docker", "inspect", "-f", "{{.State.OOMKilled}} {{.State.Running}}", NAME, check=False)
    try:
        cpu = (cpu_usec() - c0) / 1e6
    except Exception:
        cpu = None
    return {"wall_s": round(wall, 2), "cpu_s": None if cpu is None else round(cpu, 2), "status": status,
            "pdf_pages": pages, "pdf_bytes": size, "mem_peak_mib": None, "state_oomkilled_running": oom,
            "error": err}


def main(files_dir, log_path):
    files_dir, log = Path(files_dir), Path(log_path)
    digest = sh("docker", "pull", "-q", IMAGE)
    image_id = sh("docker", "image", "inspect", "-f", "{{index .RepoDigests 0}}", IMAGE)
    version = sh("docker", "image", "inspect", "-f",
                 '{{index .Config.Labels "org.opencontainers.image.version"}}', IMAGE, check=False) or "unknown"
    header = {"image": IMAGE, "pulled": digest, "repo_digest": image_id, "gotenberg_version_output": version[:200],
              "api_timeout": API_TIMEOUT or "default", "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(log, "a", encoding="utf-8") as out:
        out.write(json.dumps({"header": header}) + "\n")
        for cpus, mem in SIZES:
            for f in FILES:
                path = files_dir / f
                health_s = start(cpus, mem)
                for run in range(1 + WARM_RUNS):
                    rec = convert(path)
                    running = rec["state_oomkilled_running"].endswith("true")
                    peak = mem_peak() if running else None
                    rec["mem_peak_mib"] = None if peak is None else round(peak / 2**20, 1)
                    rec.update({"cpus": cpus, "memory": mem, "file": f, "run": "cold" if run == 0 else f"warm{run}",
                                "file_mb": round(path.stat().st_size / 1e6, 1), "health_s": round(health_s, 2)})
                    out.write(json.dumps(rec) + "\n")
                    out.flush()
                    print(f"[{cpus} vCPU {mem}] {f} {rec['run']}: status {rec['status']} wall {rec['wall_s']} s "
                          f"cpu {rec['cpu_s']} s peak {rec['mem_peak_mib']} MiB pages {rec['pdf_pages']} "
                          f"{rec['state_oomkilled_running']}")
                    if rec["status"] != 200:
                        break
                sh("docker", "rm", "-f", NAME, check=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
