from __future__ import annotations

import io

from PIL import Image

from scamshield.reports import SubmitInput, submit_report

DESC = "Someone called and asked me to send money back for a mistaken transfer."


def png_bytes(color=(10, 90, 83)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (12, 12), color).save(b, "PNG")
    return b.getvalue()


def submit(db, settings, value="0700000001", itype="phone", reporter=None, bucket="b-1", category="reversal", org=None, **kw):
    inp = SubmitInput(itype=itype, value=value, description=kw.pop("description", DESC), category=category, consent_privacy=True, consent_truth=True, **kw)
    res = submit_report(db, settings, inp, reporter=reporter, bucket=bucket, owning_org_id=org.id if org else None)
    db.commit()
    return res
