#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pypdf>=4"]
# ///
"""Build the ready-to-share pack for people outside the review: the report as
Word, the flagged emails as one bookmarked PDF, and a CSV index.

Run after collect_flagged.py and after the report is written:
  uv run scripts/build_share_pack.py --case-dir <case-dir> --findings <case-dir>/findings.json \
      --report <case-dir>/<report>.md --case-name "<case name>"

Writes <case-dir>/share/:
  <Case>_Report.docx       report; "idx-N" ids become "Email 0001 (bundle p. 5)"
  <Case>_Email_Bundle.pdf  each flagged email in date order, then its PDF
                           attachments; one bookmark per email and attachment
  <Case>_Email_Index.csv   one row per email with its page in the bundle
  Native_Files/<ref>/      attachments that can't go in a PDF (Excel, Word...)

Needs Google Chrome or Chromium (renders emails to PDF) and macOS `textutil`
(writes the .docx).
"""
import argparse
import base64
import csv
import email
import email.policy
import html
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

logging.getLogger("pypdf").setLevel(logging.ERROR)  # damaged-PDF checks are expected to warn

IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
# Blocks scripts and every remote load (tracking pixels, web fonts) while emails render.
CSP = ("default-src 'none'; img-src data:; style-src 'unsafe-inline'; "
       "font-src data:; frame-src 'none'")
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser",
]
PAGE_CSS = """
body { font-family: -apple-system, Helvetica, Arial, sans-serif; font-size: 11pt; }
.hdr { border: 1px solid #999; border-collapse: collapse; width: 100%; margin-bottom: 16px; }
.hdr th, .hdr td { border: 1px solid #ccc; padding: 4px 8px; text-align: left; vertical-align: top; }
.hdr th { background: #eee; width: 110px; }
.ref { font-size: 16pt; font-weight: bold; margin: 0 0 8px; }
.att { page-break-before: always; }
.att img { max-width: 100%; }
pre.body { white-space: pre-wrap; font-family: inherit; }
"""


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .") or "unnamed"


def find_chrome(explicit):
    for c in ([explicit] if explicit else CHROME_CANDIDATES):
        path = c if Path(c).exists() else shutil.which(c)
        if path:
            return path
    raise SystemExit("Chrome or Chromium not found. Install Google Chrome or pass --chrome <path>.")


def html_to_pdf(chrome, html_path: Path, pdf_path: Path, profile: Path):
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--user-data-dir={profile}", "--host-resolver-rules=MAP * ~NOTFOUND",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True, timeout=180)
    if not pdf_path.exists():
        raise SystemExit(f"Chrome did not produce {pdf_path}")


def readable_pdf(data: bytes, tmp: Path) -> bool:
    p = tmp / "check.pdf"
    p.write_bytes(data)
    try:
        r = PdfReader(p)
        return not r.is_encrypted and len(r.pages) > 0
    except Exception:
        return False


def email_parts(msg):
    """Return (html_body, text_body, cid_images, attachments). Inline images
    referenced by cid: are shown in the body, not listed as attachments."""
    html_body = text_body = None
    cids, atts = {}, []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        filename = part.get_filename()
        cid = (part.get("Content-ID") or "").strip("<> ")
        if part.get_content_disposition() == "attachment" or filename:
            data = part.get_payload(decode=True) or b""
            if data:
                atts.append({"name": safe_name(filename or "unnamed"), "ctype": ctype,
                             "data": data, "cid": cid})
            continue
        if ctype in IMAGE_TYPES and cid:
            cids[cid] = (ctype, part.get_payload(decode=True) or b"")
        elif ctype == "text/html" and html_body is None:
            html_body = part.get_content()
        elif ctype == "text/plain" and text_body is None:
            text_body = part.get_content()
    for a in atts:  # images with a filename can still be cid-referenced inline
        if a["cid"] and a["ctype"] in IMAGE_TYPES:
            cids.setdefault(a["cid"], (a["ctype"], a["data"]))
    return html_body, text_body, cids, atts


def data_uri(ctype, data):
    return f"data:{ctype};base64,{base64.b64encode(data).decode()}"


def render_email_html(ref, msg, html_body, text_body, cids, atts, att_notes):
    def hv(name):
        return html.escape(str(msg.get(name) or ""))
    if html_body:
        # Repeat until stable: one pass lets a nested "<me<meta>ta ...>" rebuild a tag.
        # <meta refresh> is not covered by CSP and could load a local file into the PDF.
        body, prev = html_body, None
        while body != prev:
            prev = body
            body = re.sub(r"<(script|base|meta)\b[^>]*>(.*?</script>)?", "", body, flags=re.I | re.S)
        used = set()

        def swap(m):
            cid = m.group(1)
            if cid in cids:
                used.add(cid)
                return data_uri(*cids[cid])
            return ""
        body = re.sub(r"cid:([^\"'\s>)]+)", swap, body)
        body = re.sub(r"<img\b[^>]*\bsrc\s*=\s*[\"']?(https?:)?//[^>]*>", "[external image not loaded]", body, flags=re.I)
    else:
        used = set()
        body = f'<pre class="body">{html.escape(text_body or "(no body text)")}</pre>'
    att_rows = "".join(f"<li>{html.escape(a['name'])}: {html.escape(att_notes[i])}</li>"
                       for i, a in enumerate(atts) if a["cid"] not in used)
    pages = "".join(
        f'<div class="att"><p><b>Email {ref}, attachment: {html.escape(a["name"])}</b></p>'
        f'<img src="{data_uri(a["ctype"], a["data"])}"></div>'
        for i, a in enumerate(atts) if att_notes[i] == "image, shown after the email" and a["cid"] not in used)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}"><style>{PAGE_CSS}</style></head><body>
<p class="ref">Email {ref}</p>
<table class="hdr">
<tr><th>Date</th><td>{hv('Date')}</td></tr><tr><th>From</th><td>{hv('From')}</td></tr>
<tr><th>To</th><td>{hv('To')}</td></tr><tr><th>Cc</th><td>{hv('Cc')}</td></tr>
<tr><th>Subject</th><td>{hv('Subject')}</td></tr>
<tr><th>Attachments</th><td><ul style="margin:0;padding-left:18px">{att_rows or '<li>None</li>'}</ul></td></tr>
</table>
{body}
{pages}
</body></html>""", used


def inline_md(s: str) -> str:
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"(?<![\w*])[*_](?!\s)(.+?)(?<!\s)[*_](?![\w*])", r"<i>\1</i>", s)


def md_to_html(md: str) -> str:
    """Just enough Markdown for the report template: headings, quotes, lists,
    tables and paragraphs."""
    out, para, i = [], [], 0
    lines = md.splitlines()

    def flush():
        if para:
            out.append(f"<p>{inline_md(' '.join(para))}</p>")
            para.clear()
    while i < len(lines):
        raw = lines[i]
        line = html.escape(raw.strip(), quote=False)
        if not line:
            flush()
        elif m := re.match(r"(#{1,6})\s+(.*)", line):
            flush()
            out.append(f"<h{len(m[1])}>{inline_md(m[2])}</h{len(m[1])}>")
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            tag = "th"
            body = ""
            for r in rows:
                body += "<tr>" + "".join(f"<{tag}>{inline_md(html.escape(c, quote=False))}</{tag}>" for c in r) + "</tr>"
                tag = "td"
            out.append(f'<table border="1" cellpadding="4" style="border-collapse:collapse">{body}</table>')
            continue
        elif line.startswith("&gt;"):
            flush()
            out.append(f"<blockquote><i>{inline_md(line[4:].strip())}</i></blockquote>")
        elif m := re.match(r"([-*]|\d+\.)\s+(.*)", line):
            flush()
            tag = "ol" if m[1][0].isdigit() else "ul"
            items = []
            while i < len(lines) and (m := re.match(r"\s*([-*]|\d+\.)\s+(.*)", lines[i])):
                items.append(f"<li>{inline_md(html.escape(m[2], quote=False))}</li>")
                i += 1
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue
        else:
            para.append(line)
        i += 1
    flush()
    return ("<!doctype html><html><head><meta charset='utf-8'></head>"
            "<body style='font-family:Helvetica,Arial,sans-serif'>" + "\n".join(out) + "</body></html>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case-dir", required=True, type=Path)
    ap.add_argument("--findings", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--case-name", required=True)
    ap.add_argument("--out-dir", type=Path, help="default: <case-dir>/share")
    ap.add_argument("--chrome", help="path to Chrome/Chromium if not auto-detected")
    args = ap.parse_args()

    chrome = find_chrome(args.chrome)
    if not shutil.which("textutil"):
        raise SystemExit("textutil not found; the .docx step needs macOS.")
    out = args.out_dir or args.case_dir / "share"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Refusing to overwrite {out}; remove it or pass a fresh --out-dir")
    out.mkdir(parents=True, exist_ok=True)
    prefix = safe_name(args.case_name).replace(" ", "_")

    manifest = {f"idx-{m['index']}": m for m in load_jsonl(args.case_dir / "manifest.jsonl")}
    finding_by_id = {}
    for f in json.loads(args.findings.read_text())["findings"]:
        if f.get("relevant") and f["message_id"] in manifest:
            finding_by_id.setdefault(f["message_id"], f)
    ordered = sorted(finding_by_id, key=lambda mid: (manifest[mid]["date"] or "9999", manifest[mid]["index"]))

    writer, rows, ref_of = PdfWriter(), [], {}
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        for n, mid in enumerate(ordered, 1):
            ref, m, f = f"{n:04d}", manifest[mid], finding_by_id[mid]
            eml = args.case_dir / "flagged_emails" / f"{(m['date'] or 'undated')[:10]}_{mid}" / "original.eml"
            if not eml.exists():
                raise SystemExit(f"Missing {eml}; run collect_flagged.py first")
            msg = email.message_from_bytes(eml.read_bytes(), policy=email.policy.default)
            html_body, text_body, cids, atts = email_parts(msg)

            notes, pdf_atts, natives = [], [], []
            for a in atts:
                if a["ctype"] == "application/pdf" or a["name"].lower().endswith(".pdf"):
                    if readable_pdf(a["data"], tmp):
                        notes.append("PDF, inserted after the email")
                        pdf_atts.append(a)
                        continue
                    note = "PDF could not be opened (damaged or password-protected)"
                elif a["ctype"] in IMAGE_TYPES:
                    notes.append("image, shown after the email")
                    continue
                else:
                    note = "not shown in this PDF"
                dest = out / "Native_Files" / ref / a["name"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(a["data"])
                notes.append(f"{note}; original file in Native_Files/{ref}/")
                natives.append(a["name"])

            page_html = tmp / f"{ref}.html"
            page, used = render_email_html(ref, msg, html_body, text_body, cids, atts, notes)
            page_html.write_text(page)
            page_pdf = tmp / f"{ref}.pdf"
            html_to_pdf(chrome, page_html, page_pdf, tmp / "chrome-profile")
            # Defence in depth: the printed page must be this email, not somewhere it navigated to.
            if f"Email {ref}" not in PdfReader(page_pdf).pages[0].extract_text():
                raise SystemExit(f"Email {ref} ({mid}) did not render as expected; check {eml}")

            start = len(writer.pages)
            writer.append(str(page_pdf))
            subject = str(msg.get("Subject") or "(no subject)")
            parent = writer.add_outline_item(f"{ref}  {(m['date'] or 'undated')[:10]}  {subject}", start)
            for a in pdf_atts:
                p = tmp / "att.pdf"
                p.write_bytes(a["data"])
                att_start = len(writer.pages)
                writer.append(str(p))
                writer.add_outline_item(a["name"], att_start, parent=parent)

            ref_of[mid] = (ref, start + 1)
            rows.append({
                "Ref": ref, "Date": m["date"] or "", "From": str(msg.get("From") or ""),
                "To": str(msg.get("To") or ""), "Cc": str(msg.get("Cc") or ""), "Subject": subject,
                "Matched terms": "; ".join(f.get("matched_terms") or []),
                "Category": f.get("category") or "", "Quote": f.get("quote") or "",
                "Bundle page": start + 1,
                "Attachments": "; ".join(a["name"] for a in atts if a["cid"] not in used),
                "Native files": "; ".join(f"Native_Files/{ref}/{x}" for x in natives),
                "Source id": mid,
            })

        writer.page_mode = "/UseOutlines"
        with open(out / f"{prefix}_Email_Bundle.pdf", "wb") as fh:
            writer.write(fh)

        with open(out / f"{prefix}_Email_Index.csv", "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["Ref"])
            w.writeheader()
            # Email text is untrusted: stop Excel reading a cell like "=HYPERLINK(...)" as a formula.
            w.writerows({k: "'" + v if isinstance(v, str) and v[:1] in "=+-@\t\r" else v
                         for k, v in r.items()} for r in rows)

        def cite(mt):
            if mt[0] not in ref_of:
                return mt[0]
            ref, page = ref_of[mt[0]]
            return f"Email {ref} (bundle p. {page})"
        report_md = re.sub(r"\bidx-\d+\b", cite, args.report.read_text())
        report_html = tmp / "report.html"
        report_html.write_text(md_to_html(report_md))
        subprocess.run(["textutil", "-convert", "docx", "-output",
                        str(out / f"{prefix}_Report.docx"), str(report_html)],
                       check=True, capture_output=True)

    print(f"Wrote {len(rows)} emails ({len(writer.pages)} pages) to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
