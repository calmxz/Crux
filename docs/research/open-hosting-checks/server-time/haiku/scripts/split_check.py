"""#726 item 5: page-split sizes and token counts, a plain pypdf copy against a pruned one,
plus the machine the runs used. Token counting is free.

Usage: python split_check.py <files_dir> > ../logs/split-check-<date>.txt
ASCII-only output.
"""
import base64
import io
import platform
import subprocess
import sys

from pypdf import PdfReader, PdfWriter

from common import HAIKU, client
from pdf_parts import part_b64


def plain_b64(path, n):
    r = PdfReader(path)
    w = PdfWriter()
    for i in range(n):
        w.add_page(r.pages[i])
    buf = io.BytesIO()
    w.write(buf)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


def count(c, data):
    return c.messages.count_tokens(model=HAIKU, messages=[{"role": "user", "content": [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
        {"type": "text", "text": "x"}]}]).input_tokens


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()


def main(files_dir):
    print("== machine")
    print("cpu:", sh("powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"))
    print("os:", platform.platform())
    print("docker:", sh("docker", "info", "--format",
                        "{{.ServerVersion}}, {{.NCPU}} CPUs, cgroup v{{.CgroupVersion}}, kernel {{.KernelVersion}}"))
    c = client()
    for name in ("worst-case-100-slides.pptx.pdf", "worst-case-100-pages.docx.pdf"):
        path = f"{files_dir}/{name}"
        print(f"== {name}")
        for n in (1, 20, 50):
            raw, pruned = plain_b64(path, n), part_b64(PdfReader(path), 0, n)
            print(f"{n} pages: plain copy {len(raw)} base64 chars, {count(c, raw)} tokens; "
                  f"pruned {len(pruned)} base64 chars, {count(c, pruned)} tokens")


if __name__ == "__main__":
    main(sys.argv[1])
