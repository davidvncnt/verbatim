"""
verbatim.ocr.mistral — the paid, model-based recognition path.

This is the only place in verbatim where a language model touches the text, and
it is the path that produced hallucinations in the earlier attempt. It is off by
default, it is only reachable for pages that hold no text of their own, and
every passage it produces is marked `recognised_model` so that neither the
report nor the reviewer can present it as extracted.

Long documents are sent in batches so that one oversized request cannot fail a
whole file, and a failed batch only costs the pages inside it.
"""

from __future__ import annotations

import statistics


def _batch(pdf_path, page_numbers, args, log):
    """Send one batch of pages to the OCR API. Returns ({page: markdown}, scores)."""
    import base64
    import io
    import json

    import requests
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for n in page_numbers:
        writer.add_page(reader.pages[n - 1])
    buf = io.BytesIO()
    writer.write(buf)
    payload = {
        "model": args.mistral_model,
        "document": {
            "type": "document_url",
            "document_url": "data:application/pdf;base64,"
                            + base64.b64encode(buf.getvalue()).decode(),
        },
        "confidence_scores_granularity": "page",
        "include_image_base64": False,
    }
    r = requests.post("https://api.mistral.ai/v1/ocr",
                      headers={"Authorization": f"Bearer {args.mistral_key}",
                               "Content-Type": "application/json"},
                      data=json.dumps(payload), timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"Mistral OCR refused the request "
                           f"({r.status_code}): {r.text[:300]}")
    out, scores = {}, []
    for i, pg in enumerate(r.json().get("pages", [])):
        if i < len(page_numbers):
            out[page_numbers[i]] = pg.get("markdown", "") or ""
            cs = pg.get("confidence_scores") or {}
            if cs.get("average_page_confidence_score") is not None:
                scores.append(float(cs["average_page_confidence_score"]))
    return out, scores


def mistral_ocr(pdf_path, page_numbers, args, log=print):
    """Send the listed pages to the Mistral OCR API. Returns {page_no: text}."""
    size = max(1, int(args.mistral_batch_pages))
    batches = [page_numbers[i:i + size]
               for i in range(0, len(page_numbers), size)]
    texts, scores, failed, per_page = {}, [], [], {}
    for k, batch in enumerate(batches, 1):
        if len(batches) > 1:
            log(f"   Mistral OCR: batch {k}/{len(batches)} "
                f"(pages {batch[0]}-{batch[-1]})")
        try:
            got, sc = _batch(pdf_path, batch, args, log)
            texts.update(got)
            scores += sc
            for n, v in zip(batch, sc):
                per_page[n] = v * 100.0
        except Exception as exc:
            failed += batch
            log(f"   ! Mistral OCR failed on pages {batch[0]}-{batch[-1]}: {exc}")
    if scores:
        log(f"   Mistral OCR confidence: {statistics.mean(scores):.0%} "
            f"over {len(page_numbers) - len(failed)} page(s)")
    blank = [p for p, t in texts.items() if not t.strip()]
    if blank:
        log(f"   ! Mistral returned nothing for {len(blank)} page(s) "
            f"({ranges(blank)}); the PDF's own text layer was kept for them")
    return texts, per_page


def ranges(numbers):
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'"""
    out, nums = [], sorted(set(numbers))
    start = prev = nums[0]
    for n in nums[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        out.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    return ", ".join(out)
