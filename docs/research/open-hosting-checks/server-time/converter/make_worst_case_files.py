"""Build two worst-case lesson files for the converter benchmark (#726 item 5).

- worst-case-100-slides.pptx: 100 slides. Most carry a full-size photo; native charts,
  tables, equations (OMML) and mixed layouts are spread across the deck.
- worst-case-100-pages.docx: 100 pages. Most carry a full-width photo; tables,
  equations (OMML) and chart images are spread across the document.

Photos are generated, each one different, so the files cannot share image parts.
Both files stay under the spec's 50 MB per file. They are heavier than a typical
lecture deck on purpose, so the converter's figures err high.

Usage: python make_worst_case_files.py <out_dir>
Needs: python-pptx, python-docx, pillow. ASCII-only output.
"""
import io
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import parse_xml
from docx.shared import Inches as DInches, Pt as DPt

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

SEED = 726
PAGES = 100
TOPICS = ["Limits", "Derivatives", "Chain rule", "Integrals", "Series", "Vectors",
          "Matrices", "Probability", "Statistics", "Kinematics"]
EQUATIONS = [
    # (plain-text fallback, OMML body inside <m:oMath>)
    ("x = (-b +/- sqrt(b^2 - 4ac)) / 2a",
     '<m:r><m:t>x=</m:t></m:r><m:f><m:num><m:r><m:t>-b&#177;</m:t></m:r><m:rad><m:radPr><m:degHide m:val="1"/></m:radPr>'
     '<m:deg/><m:e><m:sSup><m:e><m:r><m:t>b</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup>'
     '<m:r><m:t>-4ac</m:t></m:r></m:e></m:rad></m:num><m:den><m:r><m:t>2a</m:t></m:r></m:den></m:f>'),
    ("integral from 0 to 1 of x^2 dx = 1/3",
     '<m:nary><m:naryPr><m:chr m:val="&#8747;"/></m:naryPr><m:sub><m:r><m:t>0</m:t></m:r></m:sub><m:sup><m:r><m:t>1</m:t></m:r></m:sup>'
     '<m:e><m:sSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup><m:r><m:t>dx</m:t></m:r></m:e></m:nary>'
     '<m:r><m:t>=</m:t></m:r><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>3</m:t></m:r></m:den></m:f>'),
    ("sum from n=1 to infinity of 1/n^2 = pi^2/6",
     '<m:nary><m:naryPr><m:chr m:val="&#8721;"/></m:naryPr><m:sub><m:r><m:t>n=1</m:t></m:r></m:sub><m:sup><m:r><m:t>&#8734;</m:t></m:r></m:sup>'
     '<m:e><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:sSup><m:e><m:r><m:t>n</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:den></m:f></m:e></m:nary>'
     '<m:r><m:t>=</m:t></m:r><m:f><m:num><m:sSup><m:e><m:r><m:t>&#960;</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:num><m:den><m:r><m:t>6</m:t></m:r></m:den></m:f>'),
]
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
A14_NS = "http://schemas.microsoft.com/office/drawing/2010/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
LOREM = ("A worked example builds the idea step by step, then the learner tries a fresh problem "
         "with the method visible. Each step names the rule it uses, and the last line checks the answer. ")


def photo(rng, w=1920, h=1080, quality=85):
    """A photo-like JPEG: smooth colour fields plus grain, so it compresses like a real photo."""
    small = Image.new("RGB", (32, 18))
    small.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(32 * 18)])
    img = small.resize((w, h), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    for _ in range(40):
        x, y = rng.randrange(w), rng.randrange(h)
        r = rng.randrange(20, 220)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(rng.randrange(256), rng.randrange(256), rng.randrange(256)))
    img = img.filter(ImageFilter.GaussianBlur(3))
    grain = Image.effect_noise((w, h), 28).convert("RGB")
    img = Image.blend(img, grain, 0.18)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    return buf


def chart_image(rng, w=1600, h=700):
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    n = 12
    for i in range(n):
        v = rng.randrange(80, h - 60)
        x0 = 60 + i * (w - 120) // n
        d.rectangle([x0, h - 40 - v, x0 + (w - 120) // n - 20, h - 40], fill=(40 + i * 15, 90, 200 - i * 10))
    d.line([50, h - 40, w - 40, h - 40], fill="black", width=3)
    d.line([50, 20, 50, h - 40], fill="black", width=3)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def kinds(i):
    """Content mix for page i (0-based): photo on most pages, plus one extra element."""
    has_photo = i % 10 not in (3, 7)  # 80 of 100 pages carry a photo
    extra = ["chart", "table", "equation", "mixed", None][i % 5]
    return has_photo, extra


# ---------------------------------------------------------------- PowerPoint

def pptx_equation(slide, left, top, width, height, fallback, omml):
    tb = slide.shapes.add_textbox(left, top, width, height)
    sp = tb._element
    p = tb.text_frame.paragraphs[0]
    p_el = p._p
    ac = etree.SubElement(p_el, f"{{{MC_NS}}}AlternateContent", nsmap={"mc": MC_NS})
    choice = etree.SubElement(ac, f"{{{MC_NS}}}Choice", Requires="a14", nsmap={"a14": A14_NS})
    m14 = etree.fromstring(
        f'<a14:m xmlns:a14="{A14_NS}" xmlns:m="{M_NS}"><m:oMathPara><m:oMath>{omml}</m:oMath></m:oMathPara></a14:m>')
    choice.append(m14)
    fb = etree.SubElement(ac, f"{{{MC_NS}}}Fallback")
    r = etree.SubElement(fb, qn("a:r"))
    etree.SubElement(r, qn("a:t")).text = fallback
    return sp


def build_pptx(path, rng):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    layout = prs.slide_layouts[5]  # title only
    for i in range(PAGES):
        s = prs.slides.add_slide(layout)
        topic = TOPICS[i % len(TOPICS)]
        s.shapes.title.text = f"{topic}: part {i + 1}"
        has_photo, extra = kinds(i)
        if has_photo:
            if extra in ("chart", "table", "mixed"):
                s.shapes.add_picture(photo(rng), Inches(0.4), Inches(1.4), width=Inches(6.2))
            else:
                # Full-bleed photo behind the title and text (moved to the back of the shape tree).
                pic = s.shapes.add_picture(photo(rng), Inches(0), Inches(0),
                                           width=prs.slide_width, height=prs.slide_height)
                tree = s.shapes._spTree
                tree.remove(pic._element)
                tree.insert(2, pic._element)
        body = s.shapes.add_textbox(Inches(0.5), Inches(6.2), Inches(12.3), Inches(1.1)).text_frame
        body.word_wrap = True
        body.text = LOREM
        for para in body.paragraphs:
            for run in para.runs:
                run.font.size = Pt(14)
        if extra in ("chart", "mixed"):
            cd = CategoryChartData()
            cd.categories = [f"Q{k}" for k in range(1, 9)]
            cd.add_series("Score", [rng.randrange(10, 100) for _ in range(8)])
            cd.add_series("Time", [rng.randrange(10, 100) for _ in range(8)])
            ctype = [XL_CHART_TYPE.COLUMN_CLUSTERED, XL_CHART_TYPE.LINE_MARKERS, XL_CHART_TYPE.BAR_STACKED][i % 3]
            s.shapes.add_chart(ctype, Inches(6.9), Inches(1.4), Inches(6), Inches(2.3 if extra == "mixed" else 4.6), cd)
        if extra in ("table", "mixed"):
            rows, cols = (6, 5) if extra == "mixed" else (10, 6)
            top = Inches(3.9) if extra == "mixed" else Inches(1.4)
            t = s.shapes.add_table(rows, cols, Inches(6.9), top, Inches(6), Inches(2.2 if extra == "mixed" else 4.6)).table
            for r in range(rows):
                for c in range(cols):
                    t.cell(r, c).text = f"h{c}" if r == 0 else f"{rng.random() * 100:.2f}"
        if extra == "equation":
            fb, om = EQUATIONS[i % len(EQUATIONS)]
            pptx_equation(s, Inches(1), Inches(4.8), Inches(11), Inches(1.2), fb, om)
    prs.save(path)


# ---------------------------------------------------------------- Word

def docx_equation(doc, omml):
    p = doc.add_paragraph()
    p._p.append(parse_xml(f'<m:oMathPara xmlns:m="{M_NS}"><m:oMath>{omml}</m:oMath></m:oMathPara>'))


def build_docx(path, rng):
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = DInches(0.8)
    style = doc.styles["Normal"]
    style.font.size = DPt(10)
    for i in range(PAGES):
        topic = TOPICS[i % len(TOPICS)]
        doc.add_heading(f"{topic}: page {i + 1}", level=1)
        has_photo, extra = kinds(i)
        if has_photo:
            doc.add_picture(photo(rng), width=DInches(6.4 if extra is None else 5.2))
        doc.add_paragraph(LOREM)
        if extra in ("chart", "mixed"):
            doc.add_picture(chart_image(rng), width=DInches(4.6 if extra == "mixed" else 6.4))
        if extra in ("table", "mixed"):
            rows, cols = (4, 5) if extra == "mixed" else (12, 6)
            t = doc.add_table(rows=rows, cols=cols)
            t.style = "Table Grid"
            for r in range(rows):
                for c in range(cols):
                    t.cell(r, c).text = f"h{c}" if r == 0 else f"{rng.random() * 100:.2f}"
        if extra == "equation":
            for fb, om in EQUATIONS:
                docx_equation(doc, om)
        if i < PAGES - 1:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.save(path)


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    p1 = out / "worst-case-100-slides.pptx"
    build_pptx(p1, rng)
    p2 = out / "worst-case-100-pages.docx"
    build_docx(p2, rng)
    for p in (p1, p2):
        mb = p.stat().st_size / 1e6
        print(f"[OK] {p.name}: {mb:.1f} MB {'(over 50 MB!)' if mb > 50 else ''}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
