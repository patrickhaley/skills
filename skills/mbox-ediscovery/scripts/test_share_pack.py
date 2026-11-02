#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pypdf>=4"]
# ///
"""End-to-end check for build_share_pack.py on a synthetic mailbox:
ingest -> collect_flagged -> build_share_pack, then assert on the output.

Run:  uv run scripts/test_share_pack.py
"""
import csv
import io
import json
import mailbox
import subprocess
import sys
import tempfile
import zipfile
from email.message import EmailMessage
from pathlib import Path

from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).resolve().parent
PNG = bytes.fromhex(  # 1x1 transparent PNG
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5f0000000049454e44ae426082")


def two_page_pdf() -> bytes:
    w = PdfWriter()
    w.add_blank_page(612, 792)
    w.add_blank_page(612, 792)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def build_mbox(path: Path):
    box = mailbox.mbox(str(path))
    a = EmailMessage()
    a["From"], a["To"], a["Date"] = "jane@example.com", "john@example.com", "Mon, 05 Feb 2024 10:00:00 +0000"
    a["Subject"] = "Signed quote"
    a.set_content("Plain fallback")
    a.add_alternative('<p>See the <b>quote</b>.</p><img src="cid:logo1">'
                      '<img src="https://tracker.example.com/p.gif"><script>alert(1)</script>', subtype="html")
    a.get_payload()[1].add_related(PNG, "image", "png", cid="<logo1>")
    a.add_attachment(two_page_pdf(), maintype="application", subtype="pdf", filename="Quote.pdf")
    a.add_attachment(b"col1,col2\n1,2\n", maintype="application",
                     subtype="vnd.ms-excel", filename="Costs.xls")
    box.add(a)
    b = EmailMessage()
    b["From"], b["To"], b["Date"] = "john@example.com", "jane@example.com", "Sun, 04 Feb 2024 09:00:00 +0000"
    b["Subject"] = "Deposit <question>"
    b.set_content("Can we discuss the deposit?\n\n<not html>")
    b.add_attachment(b"%PDF-broken", maintype="application", subtype="pdf", filename="Broken.pdf")
    box.add(b)
    box.flush()


def run(*cmd):
    subprocess.run(cmd, check=True, cwd=HERE)


def main():
    with tempfile.TemporaryDirectory() as t:
        t = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(t)  # pass a dir to keep the output
        mbox, case = t / "test.mbox", t / "case"
        build_mbox(mbox)
        run(sys.executable, "ingest.py", "--mbox", str(mbox), "--out-dir", str(case))
        findings = {"findings": [
            {"message_id": "idx-0", "relevant": True, "matched_terms": ["quote"], "quote": "See the quote."},
            {"message_id": "idx-1", "relevant": True, "matched_terms": ["deposit"], "quote": "Can we discuss the deposit?"},
        ]}
        (case / "findings.json").write_text(json.dumps(findings))
        run(sys.executable, "collect_flagged.py", "--case-dir", str(case),
            "--findings", str(case / "findings.json"), "--mbox", str(mbox))
        report = case / "report.md"
        report.write_text("# eDiscovery review: Test\n\n> Facts only.\n\n**Generated:** 2024-03-01\n\n"
                          "| Date | Quote | Source |\n|---|---|---|\n| 2024-02-05 | \"See the quote.\" | idx-0 |\n\n"
                          "- Unclassified: idx-99\n")
        run(sys.executable, "build_share_pack.py", "--case-dir", str(case), "--findings",
            str(case / "findings.json"), "--report", str(report), "--case-name", "Test Case")

        share = case / "share"
        rows = list(csv.DictReader(open(share / "Test_Case_Email_Index.csv", encoding="utf-8-sig")))
        assert [r["Source id"] for r in rows] == ["idx-1", "idx-0"], "emails must be in date order"
        assert rows[0]["Ref"] == "0001" and rows[0]["Bundle page"] == "1"
        assert rows[1]["Attachments"] == "Quote.pdf; Costs.xls", rows[1]["Attachments"]  # inline logo not listed
        assert rows[1]["Native files"] == "Native_Files/0002/Costs.xls"
        assert (share / "Native_Files/0001/Broken.pdf").exists(), "unreadable PDF goes to native files"

        bundle = PdfReader(share / "Test_Case_Email_Bundle.pdf")
        email2_start = int(rows[1]["Bundle page"]) - 1
        outline = bundle.outline
        assert outline[0].title.startswith("0001") and outline[1].title.startswith("0002"), outline
        assert outline[2][0].title == "Quote.pdf"  # child of email 0002
        assert bundle.get_destination_page_number(outline[2][0]) == len(bundle.pages) - 2  # 2-page PDF at the end
        assert bundle.pages[email2_start].images, "inline cid image must be embedded"
        text = "".join(p.extract_text() for p in bundle.pages)
        assert "[external image not loaded]" in text and "<not html>" in text and "Deposit <question>" in text, "plain text must be escaped, not parsed"

        docx = zipfile.ZipFile(share / "Test_Case_Report.docx").read("word/document.xml").decode()
        assert "Email 0002 (bundle p. " in docx, "idx ids must become email refs"
        assert "idx-99" in docx, "ids outside the bundle stay as they are"
        assert "idx-0" not in docx
    print("share pack test passed")


if __name__ == "__main__":
    main()
