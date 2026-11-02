#!/usr/bin/env python3
"""Generate a small synthetic mbox fixture for testing the eDiscovery ingest
pipeline. Entirely fabricated data - no real names, addresses, or content.

Produces examples/sample.mbox with:
  - a 3-message thread via Message-Id/In-Reply-To/References
  - a duplicate attachment across two messages (tests hash-based dedup)
  - a calendar invite and an out-of-office auto-reply (tests noise tagging)

Run:
  python3 generate_fixture.py
"""
import mailbox
from email.message import EmailMessage
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "examples"
FIXTURE_PATH = FIXTURE_DIR / "sample.mbox"

LOGO_BYTES = b"FAKE-LOGO-BYTES-FOR-DEDUP-TEST"


def make_message(msg_id, date, sender, to, subject, body,
                  in_reply_to=None, references=None, attach=False,
                  content_type="text/plain", extra_headers=None):
    msg = EmailMessage()
    msg["Message-Id"] = msg_id
    msg["Date"] = date
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    if extra_headers:
        for k, v in extra_headers.items():
            msg[k] = v
    if content_type == "text/calendar":
        msg.set_content(body, subtype="calendar")
    else:
        msg.set_content(body)
    if attach:
        msg.add_attachment(LOGO_BYTES, maintype="application",
                            subtype="octet-stream", filename="logo.bin")
    return msg


def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    if FIXTURE_PATH.exists():
        FIXTURE_PATH.unlink()
    box = mailbox.mbox(str(FIXTURE_PATH))
    box.lock()
    try:
        box.add(make_message(
            "<1@fake-corp.test>", "Wed, 10 Jan 2024 09:00:00 -0500",
            "alice@fake-corp.test", "bob@fake-corp.test",
            "Kickoff call",
            "Hi Bob, let's kick off the new client portal project this week.",
            attach=True,
        ))
        box.add(make_message(
            "<2@fake-corp.test>", "Thu, 11 Jan 2024 10:00:00 -0500",
            "bob@fake-corp.test", "alice@fake-corp.test",
            "Re: Kickoff call",
            "Sounds good - heads up, I already started building my own "
            "portal site on the side, separate from the official one.",
            in_reply_to="<1@fake-corp.test>",
            references="<1@fake-corp.test>",
        ))
        box.add(make_message(
            "<calendar-1@fake-corp.test>", "Fri, 12 Jan 2024 08:00:00 -0500",
            "calendar-daemon@fake-corp.test", "bob@fake-corp.test",
            "Invitation: Portal sync @ Mon Jan 15",
            "BEGIN:VCALENDAR\nEND:VCALENDAR",
            content_type="text/calendar",
        ))
        box.add(make_message(
            "<3@fake-corp.test>", "Mon, 15 Jan 2024 11:00:00 -0500",
            "alice@fake-corp.test", "bob@fake-corp.test",
            "Re: Kickoff call",
            "Please don't launch that separate portal site without "
            "written approval - that's required under our agreement.",
            in_reply_to="<2@fake-corp.test>",
            references="<1@fake-corp.test> <2@fake-corp.test>",
            attach=True,
        ))
        box.add(make_message(
            "<ooo-1@fake-corp.test>", "Sat, 20 Jan 2024 09:00:00 -0500",
            "bob@fake-corp.test", "alice@fake-corp.test",
            "Automatic reply: Re: Kickoff call",
            "I am out of office until Jan 22.",
            extra_headers={"Auto-Submitted": "auto-replied"},
        ))
    finally:
        box.flush()
        box.unlock()
    print(f"Wrote {len(box)} messages to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
