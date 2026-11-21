"""Split pages out of a PDF without carrying the whole file's images.

LibreOffice (Gotenberg) PDFs give every page one shared resource dictionary that lists
every image in the file. A plain pypdf page copy therefore carries all of them: on the
worst-case deck a 1-page part was 40.8 MB. This keeps, for each page, only the XObjects
its content stream names with `Do`.
"""
import base64
import io
import re

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject

_DO = re.compile(rb"/([^\s/\[\]()<>{}%]+)\s+Do\b")


def _prune(page):
    res = page.get("/Resources")
    if res is None:
        return
    res = res.get_object()
    xo = res.get("/XObject")
    if xo is None:
        return
    xo = xo.get_object()
    contents = page.get_contents()  # a ContentStream can test falsy, so compare with None
    data = contents.get_data() if contents is not None else b""
    used = {b.decode("latin-1") for b in _DO.findall(data)}
    new_res = DictionaryObject({k: v for k, v in res.items() if k != "/XObject"})
    new_res[NameObject("/XObject")] = DictionaryObject({k: v for k, v in xo.items() if k[1:] in used})
    page[NameObject("/Resources")] = new_res


def part_bytes(reader: PdfReader, start: int, end: int) -> bytes:
    w = PdfWriter()
    for i in range(start, end):
        page = reader.pages[i]
        _prune(page)  # before add_page, which copies every object the page points at
        w.add_page(page)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def part_b64(reader: PdfReader, start: int, end: int) -> str:
    return base64.standard_b64encode(part_bytes(reader, start, end)).decode("ascii")
