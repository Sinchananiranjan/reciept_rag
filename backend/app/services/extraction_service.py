import json
import re
from typing import Dict, Any, Optional
from app.config import settings

class ExtractionService:
    def extract_structured_data(self, raw_ocr_text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured receipt data. OCR/heuristics are always attempted;
        optional vision extraction is used only as a recovery path when the
        structured result is clearly incomplete. This keeps uploads working even
        when no API key is configured."""
        if not raw_ocr_text or not raw_ocr_text.strip():
            return self._empty_extraction()

        heuristic = self._extract_with_heuristics(raw_ocr_text)

        # If OCR produced text but the table parser recovered no rows, optionally
        # ask a vision-capable model to read the original image. This is a fallback,
        # never the only extraction path.
        if image_path and settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5:
            if not heuristic.get("items") or not heuristic.get("total") or not heuristic.get("merchant_name"):
                try:
                    vision = self._extract_with_openai_vision(image_path, raw_ocr_text)
                    if vision and vision.get("items"):
                        return self._merge_extraction(heuristic, vision)
                except Exception as e:
                    print(f"OpenAI vision extraction failed ({e}), keeping OCR extraction.")

        # Text-only LLM is retained as a secondary recovery path for deployments
        # that have an API key but no vision-capable model.
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5 and not heuristic.get("items"):
            try:
                llm = self._extract_with_openai(raw_ocr_text)
                if llm.get("items"):
                    return self._merge_extraction(heuristic, llm)
            except Exception as e:
                print(f"OpenAI text extraction failed ({e}), using OCR heuristics.")

        return heuristic

    def _empty_extraction(self) -> Dict[str, Any]:
        """Returns null/empty values when no OCR text is available."""
        return {
            "merchant_name": None,
            "merchant_address": None,
            "phone": None,
            "gstin": None,
            "receipt_number": None,
            "invoice_number": None,
            "receipt_date": None,
            "receipt_time": None,
            "currency": "INR",
            "subtotal": None,
            "tax": None,
            "cgst": None,
            "sgst": None,
            "igst": None,
            "discount": None,
            "total": None,
            "payment_method": None,
            "items": []
        }

    @staticmethod
    def _merge_extraction(base: Dict[str, Any], better: Dict[str, Any]) -> Dict[str, Any]:
        """Merge recovery output without replacing reliable OCR values with nulls."""
        out = dict(base)
        for key, value in better.items():
            if key == "items":
                if value:
                    out["items"] = value
            elif value not in (None, "", []):
                out[key] = value
        return out

    def _extract_with_openai_vision(self, image_path: str, raw_ocr_text: str) -> Dict[str, Any]:
        import base64
        import urllib.request

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")

        ext = image_path.lower().rsplit(".", 1)[-1]
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/png")
        prompt = """Read this receipt image carefully and return ONLY JSON. Extract EVERY visible line item as a separate row. Never use the receipt grand total as an item total. Preserve quantity, unit price and line total exactly as printed. Do not invent values. If OCR text is supplied below, use it only as a hint and prefer the image when they conflict. For merchant_name, use the EXACT name printed in the largest/first bold title at the top of the receipt (e.g., 'DMART', 'SPAR'). Do not normalize or guess the corporate name.

Schema: merchant_name, merchant_address, phone, gstin, receipt_number, receipt_date, receipt_time, currency, subtotal, tax, cgst, sgst, igst, discount, total, payment_method, items[{product_name,quantity,unit_price,total_price,sku}]

OCR hint:
""" + raw_ocr_text

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You are an exact receipt OCR and table extraction engine. Return valid JSON only."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                ]},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return json.loads(body["choices"][0]["message"]["content"])

    def _extract_with_openai(self, raw_ocr_text: str) -> Dict[str, Any]:
        import urllib.request
        prompt = f"""
Extract receipt/invoice metadata and line items from the following OCR text into JSON format.
If a field cannot be found, set it to null. Do NOT invent or guess missing values.
For merchant_name, use the EXACT name printed in the largest/first bold title at the top of the receipt (e.g., 'DMART', 'SPAR'). Do not normalize or guess the corporate name.

JSON Schema:
{{
  "merchant_name": string | null,
  "merchant_address": string | null,
  "phone": string | null,
  "gstin": string | null,
  "receipt_number": string | null,
  "invoice_number": string | null,
  "receipt_date": string | null (Format: YYYY-MM-DD or readable date),
  "receipt_time": string | null (Format: HH:MM),
  "currency": string (e.g. "INR", "USD", "EUR", "GBP"),
  "subtotal": float | null,
  "tax": float | null,
  "cgst": float | null,
  "sgst": float | null,
  "igst": float | null,
  "discount": float | null,
  "total": float | null,
  "payment_method": string | null (e.g., "UPI", "Credit Card", "Cash"),
  "items": [
    {{
      "product_name": string,
      "quantity": float,
      "unit_price": float | null,
      "total_price": float | null,
      "sku": string | null
    }}
  ]
}}

OCR TEXT:
{raw_ocr_text}
"""
        req_data = json.dumps({
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You are a precise receipt data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
        )

        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)

    # --- Structural regexes used by the heuristic parser -----------------------------
    # A line that looks like the item-table column header, e.g. "Item Qty Price Total"
    # or "Description  Amount". Used to find where the item section BEGINS.
    _HEADER_ROW_RE = re.compile(
        r"\b(item|description|product|particulars)\b.{0,40}\b(qty|quantity|price|rate|amount|total)\b",
        re.IGNORECASE
    )
    # A line that starts the totals/summary block, e.g. "Subtotal", "Grand Total",
    # "GST", "Discount", "Payment Mode", "Thank you". Used to find where the item
    # section ENDS, and to exclude those lines from item parsing entirely.
    _SUMMARY_START_RE = re.compile(
        r"^\s*[^A-Za-z0-9]{0,3}\s*(sub[\s-]?total|grand\s*total|net\s*amount|amount\s*payable|"
        r"amount\s*due|balance\s*due|total\b|tax\b|cgst|sgst|igst|vat\b|discount|less\b|"
        r"savings\b|payment\s*mode|payment\b|change\b|thank\s*you|visit\s*again)",
        re.IGNORECASE
    )
    # Lines that are clearly receipt metadata (merchant/header/footer info), never items.
    _METADATA_LINE_RE = re.compile(
        r"\b(invoice\s*no\.?|inv\s*no\.?|bill\s*no\.?|receipt\s*no\.?|order\s*no\.?|"
        r"date\s*[:\.]|time\s*[:\.]|cashier|served\s*by|gstin|tel\b|phone|mobile|"
        r"address|counter|register|pos\s*id|table\s*no|token\s*no|customer|member|"
        r"loyalty|www\.|http|e-?mail|payment\s*mode)\b",
        re.IGNORECASE
    )
    # Currency-anchored or decimal-formatted monetary amount (NOT a bare integer like a
    # quantity, year, or invoice number). Matches "₹25", "Rs 25", "25.00", "1,224.00".
    _AMOUNT_TOKEN_RE = re.compile(
        r"(?:[₹$€£]|Rs\.?|INR)\s?(\d{1,3}(?:[,.]\d{2,3})*(?:\.\d{1,2})?)"
        r"|\b(\d{1,3}(?:[,.]\d{2,3})*\.\d{1,2})\b"
    )
    # Amount immediately after a keyword should prefer a properly decimal-formatted
    # figure (e.g. "61.20") over any bare integer noise in between (a percentage like
    # "(5%)", or a currency symbol OCR misread as a stray digit) — but still fall back
    # to a bare integer for receipts whose totals have no decimal places at all.
    _DECIMAL_AMOUNT_RE = re.compile(r"(\d{1,3}(?:[,.]\d{2,3})*\.\d{1,2})(?!\s*%)")
    _INTEGER_AMOUNT_RE = re.compile(r"(\d{1,3}(?:[,.]\d{2,3})*)(?!\s*%)")

    @staticmethod
    def _normalize_numeric_ocr(text: str) -> str:
        """
        Corrects common OCR digit confusions (O<->0, l/I<->1) but ONLY inside clusters
        that already contain a real digit, so ordinary words (e.g. "oil", "loo") are
        never touched. This repairs prices/quantities like "1O.OO" -> "10.00" without
        corrupting product names.
        """
        def repl(m: "re.Match[str]") -> str:
            s = m.group(0)
            if not re.search(r"\d", s):
                return s
            s = s.replace("O", "0").replace("o", "0")
            s = re.sub(r"[lI]", "1", s)
            return s
        return re.sub(r"[\dOolI]{2,}(?:\.[\dOolI]{1,2})?", repl, text)

    def _parse_amount_near_keyword(self, keyword_pattern: str, text: str, window: int = 45) -> Optional[float]:
        """Extract a money value after a label while aggressively ignoring OCR
        artifacts such as percentage rates, split decimals (`48 .00`) and stray
        prefix digits. Receipt labels are trusted more than isolated numbers."""
        for m in re.finditer(keyword_pattern, text, re.IGNORECASE):
            window_text = text[m.end():m.end() + window]
            # Never treat tax rates or parenthetical item counts as money.
            window_text = re.sub(r"\([^)]*%[^)]*\)", " ", window_text)
            window_text = re.sub(r"\([^)]*\b(items?|pcs?|units?)\b[^)]*\)", " ", window_text, flags=re.IGNORECASE)
            window_text = re.sub(r"\b\d+(?:\.\d+)?\s*%", " ", window_text)
            # OCR often separates decimal point: `48 .00` -> `48.00`.
            window_text = re.sub(r"(?<=\d)\s+\.(?=\d)", ".", window_text)
            # And sometimes splits a two-digit decimal: `24 58` -> `24.58`.
            window_text = re.sub(r"\b(\d{1,4})\s+(\d{2})\b", r"\1.\2", window_text)

            # Currency/decimal amount first.
            amount_re = re.compile(
                r"(?:[₹$€£]|Rs\.?|INR)?\s*(\d{1,3}(?:[,.]\d{2,3})*(?:\.\d{1,2})?|\d+\.\d{1,2})"
            )
            for am in amount_re.finditer(window_text):
                raw = am.group(1).replace(",", "")
                try:
                    value = float(raw)
                except ValueError:
                    continue
                # A percentage has already been removed. Reject obvious noise
                # before a later real amount (e.g. an isolated OCR `7`).
                if value < 0:
                    continue
                return value
        return None

    def _find_item_section(self, lines: list[str]) -> tuple[Optional[int], int, Optional[int]]:
        """Detects the [start, end) line-index range that holds the item table,
        using OCR structure (a column header row, or the first line bearing a real
        monetary amount) rather than any hardcoded product vocabulary. Also returns
        the header row's own index (if any) so callers can exclude it from both the
        item lines AND the summary text — it's structural noise, not real merchant/
        totals info, and its column words ("...Price Total") must never be mistaken
        for the receipt's actual "Total" line."""
        header_idx = None
        for i, ln in enumerate(lines):
            if self._HEADER_ROW_RE.search(ln):
                header_idx = i
                break

        if header_idx is not None:
            item_start = header_idx + 1
        else:
            item_start = None
            for i, ln in enumerate(lines):
                if i < 1:
                    # Skip the very first line: it's virtually always the merchant name.
                    continue
                if self._SUMMARY_START_RE.search(ln):
                    break
                if self._METADATA_LINE_RE.search(ln):
                    continue
                if self._AMOUNT_TOKEN_RE.search(ln):
                    item_start = i
                    break

        item_end = len(lines)
        if item_start is not None:
            for i in range(item_start, len(lines)):
                if self._SUMMARY_START_RE.search(lines[i]):
                    item_end = i
                    break

        return item_start, item_end, header_idx

    @staticmethod
    def _strip_trailing_ocr_noise(s: str) -> str:
        """Removes trailing standalone 'column artifact' tokens that Tesseract
        often invents for table borders/checkmarks — a lone symbol run (":",
        "|", "~", "<<", "=") or a single stray letter separated by whitespace
        from the real text. Runs until stable since a line can have several
        (e.g. "275.00 : :"). This must happen BEFORE quantity is read off the
        end of the line, otherwise a trailing "2 |" is misread as having no
        quantity at all instead of quantity 2."""
        prev = None
        while prev != s:
            prev = s
            s = re.sub(r"\s+[^\w\s]{1,3}$", "", s)   # trailing symbol-only token
            s = re.sub(r"\s+[A-Za-z]$", "", s)        # trailing single-letter token
            s = re.sub(r"\s+[\[(][A-Za-z]{1,8}[\]\).,:;]*$", "", s)  # OCR bracket artifact
            s = re.sub(r"\s+\d{1,3}\s+[A-Za-z]{1,8}[.:;]*$", "", s)  # `1 SEATS`-style table noise
            s = re.sub(r"\s+[\"“”'][A-Za-z]{1,4}[.:;]*$", "", s)  # quoted OCR suffix
        return s.strip()

    def _parse_item_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parses a single item-table line into product_name/quantity/unit_price/
        total_price using column structure, never a fixed product vocabulary."""
        # Strip a leading bullet / item-number prefix: "1.", "2)", "•", "*", "»", or a
        # bare leading ordinal like "1 " (digit + space before the product name).
        working = re.sub(r"^\s*(?:\(?\d{1,3}[.)]|\d{1,3}(?=\s)|[\u2022*»])\s*", "", line).strip()
        # Repair OCR-separated decimal points before looking for monetary tokens.
        # Do NOT merge `quantity price` pairs such as `2 58.00`.
        working = re.sub(r"(?<=\d)\s+\.(?=\d)", ".", working)
        if not working:
            return None

        amount_matches = list(self._AMOUNT_TOKEN_RE.finditer(working))
        unit_price: Optional[float] = None
        total_price: Optional[float] = None
        remainder = working

        if amount_matches:
            def val(m: "re.Match[str]") -> float:
                raw = m.group(1) or m.group(2)
                return float(raw.replace(",", ""))

            if len(amount_matches) == 1:
                price = val(amount_matches[0])
                unit_price = price
                total_price = price
            else:
                unit_price = val(amount_matches[-2])
                total_price = val(amount_matches[-1])
                # OCR may merge a leading quantity with the unit price, e.g.
                # `1 275.00` -> `1275.00 275.00`. When the first token is
                # exactly 1000 larger than the second, treat it as the noisy
                # quantity+price token and keep the real price.
                if len(amount_matches) == 2:
                    first = val(amount_matches[0])
                    last = val(amount_matches[-1])
                    if first >= 1000 and abs(first - last - 1000) < 0.01:
                        unit_price = last
                        total_price = last

            # Remove every matched amount span so it doesn't leak into the product name.
            spans = sorted((m.start(), m.end()) for m in amount_matches)
            pieces = []
            cursor = 0
            for s, e in spans:
                pieces.append(remainder[cursor:s])
                cursor = e
            pieces.append(remainder[cursor:])
            remainder = " ".join(pieces)

        # Drop trailing table-border noise now, BEFORE quantity is read off the
        # end of the line — otherwise "...1L 2 |" hides the real quantity "2"
        # behind a stray "|" and it silently falls back to 1.
        remainder = self._strip_trailing_ocr_noise(remainder)

        # Quantity: "x2", "X 3", "Qty: 2", "Qty2" (OCR-mangled), or a trailing bare
        # 1-3 digit integer left over once prices have been stripped out.
        quantity = 1.0
        qty_m = re.search(r"\bx\s*(\d{1,3})\b", remainder, re.IGNORECASE)
        if not qty_m:
            # "Qty"/"Qly" with common OCR letter confusions (Q<->O, t<->l/1).
            qty_m = re.search(r"\b[qo][tl1]y\.?\s*[:\.]?\s*(\d{1,3})\b", remainder, re.IGNORECASE)
        if not qty_m:
            # OCR frequently turns a quantity such as `2` into `a2`, `al`, `|2`,
            # or `=2`. Accept only a short standalone OCR artifact immediately
            # before the final digits so product names are not damaged.
            trailing_int_m = re.search(r"(?<![\d.])(\d{1,3})\s*$", remainder)
            if trailing_int_m:
                qty_m = trailing_int_m
            else:
                noisy_qty_m = re.search(r"(?:^|\s)[A-Za-z|=~:]{1,2}\s*(\d{1,3})\s*$", remainder)
                if noisy_qty_m:
                    qty_m = noisy_qty_m
                else:
                    # Quantity followed by an OCR artifact, e.g. `2 [izes` or
                    # `2 (a.`. The artifact is removed first, then this captures 2.
                    artifact_qty_m = re.search(r"\b(\d{1,3})\s*$", remainder)
                    if artifact_qty_m:
                        qty_m = artifact_qty_m
        if qty_m:
            try:
                quantity = float(qty_m.group(1))
                remainder = remainder[:qty_m.start()] + remainder[qty_m.end():]
            except ValueError:
                pass

        product_name = self._strip_trailing_ocr_noise(re.sub(r"\s{2,}", " ", remainder)).strip(" -:@,.|=~<>;")
        if len(product_name) < 2:
            return None
        # Safety net: never let a summary/metadata term through as a "product" even
        # if it slipped past the section-boundary detection.
        if self._SUMMARY_START_RE.search(product_name) or self._METADATA_LINE_RE.search(product_name):
            return None

        return {
            "product_name": product_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "sku": None
        }

    def _extract_with_heuristics(self, raw_ocr_text: str) -> Dict[str, Any]:
        """Dynamic heuristic parser for arbitrary store receipts.

        Structure, not vocabulary, drives every decision:
          1. The OCR text is split into lines.
          2. The item TABLE is located structurally (a column header row like
             "Item Qty Price Total", or otherwise the first line bearing a genuine
             monetary amount that isn't receipt metadata/summary).
          3. Everything OUTSIDE that item range (merchant header + totals footer) is
             used for merchant/date/GSTIN/phone/subtotal/tax/total/etc. Everything
             INSIDE it is used for line items. Because the two never overlap, dates,
             invoice numbers, GSTIN digits, and merchant/footer text can never be
             misread as item prices, and item text can never be misread as a total.
        """
        text = self._normalize_numeric_ocr(raw_ocr_text.strip())
        lines = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 1]

        if not lines:
            empty = self._empty_extraction()
            return empty

        item_start, item_end, header_idx = self._find_item_section(lines)
        item_lines = lines[item_start:item_end] if item_start is not None else []
        excluded = set(range(item_start, item_end)) if item_start is not None else set()
        if header_idx is not None:
            excluded.add(header_idx)
        summary_lines = [ln for i, ln in enumerate(lines) if i not in excluded]
        summary_text = "\n".join(summary_lines)

        # 1. Dynamic Merchant Name Detection (only ever looks at header lines, never
        #    at the item table or the totals footer).
        merchant_zone = lines[:min(6, item_start if item_start is not None else 6)] or lines[:6]
        merchant_name = None
        for line in merchant_zone:
            # Skip lines with fewer than 3 actual letters (usually OCR noise like `|` or `.`)
            if len(re.sub(r'[^A-Za-z]', '', line)) < 3:
                continue
            if not re.search(r"date|total|invoice|tax|subtotal|welcome|thank|bill|receipt|gstin|phone|cashier", line, re.IGNORECASE):
                cleaned = re.sub(r"^(STORE:|MERCHANT:|SHOP:|\d+\.)\s*", "", line, flags=re.IGNORECASE).strip()
                cleaned = re.sub(r"^[^A-Za-z0-9]+", "", cleaned).strip()
                if len(cleaned) > 2:
                    merchant_name = cleaned
                    break
        if not merchant_name and lines:
            # Fallback to the first line with at least some letters
            for line in lines:
                if len(re.sub(r'[^A-Za-z]', '', line)) > 1:
                    merchant_name = line.strip()
                    break
            if not merchant_name:
                merchant_name = lines[0].strip()

        # 2. Dynamic Currency Detection — unambiguous Indian tax/currency markers
        #    (₹, GSTIN, CGST/SGST/IGST) are checked FIRST and win outright, since a
        #    stray "$" is a common Tesseract misread of "₹" or a table border and
        #    must never override a receipt that is clearly in INR.
        currency = "INR"
        if re.search(r"₹|GSTIN|\bCGST\b|\bSGST\b|\bIGST\b", text, re.IGNORECASE):
            currency = "INR"
        elif re.search(r"\bUSD\b", text) or "$" in text:
            currency = "USD"
        elif "€" in text or re.search(r"\bEUR\b", text):
            currency = "EUR"
        elif "£" in text or re.search(r"\bGBP\b", text):
            currency = "GBP"
        elif re.search(r"\bRs\.?\b|\bINR\b", text):
            currency = "INR"

        # 3. Dynamic Date Detection (header/footer text only)
        receipt_date = None
        date_match = re.search(
            r"\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}[- ][A-Za-z]{3,9}[- ]\d{2,4})\b",
            summary_text
        )
        if date_match:
            receipt_date = date_match.group(1)

        # 4. Dynamic Time Detection
        receipt_time = None
        time_match = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b", summary_text)
        if time_match:
            receipt_time = time_match.group(1)

        # 5. GSTIN & Phone
        gstin = None
        gst_m = re.search(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b", summary_text)
        if gst_m:
            gstin = gst_m.group(1)

        phone = None
        phone_m = re.search(r"(?:Ph|Phone|Tel|Mobile)[:\s]*([+\d\s\-]{8,15})", summary_text, re.IGNORECASE)
        if phone_m:
            phone = phone_m.group(1).strip()

        # 6. Receipt / Invoice Number — skip past a "No."/"Number"/"#" label so the
        #    label word itself is never captured as the value, and require the
        #    captured token to actually contain a digit (real IDs always do).
        receipt_number = None
        inv_match = re.search(
            r"(?:INVOICE|INV|RECEIPT|BILL|REF|TXN|ORDER)\s*(?:NO\.?|NUMBER|#)?[:\s#]*([A-Z0-9][A-Z0-9\-]*\d[A-Z0-9\-]*)",
            summary_text, re.IGNORECASE
        )
        if inv_match:
            receipt_number = inv_match.group(1)

        # 7. Dynamic Amount Parsers — all confined to summary_text (never the item
        #    table), and keyword-anchored with word boundaries so e.g. "TOTAL" can
        #    never match inside "SUBTOTAL", and "GST" can never match inside "CGST".
        subtotal = self._parse_amount_near_keyword(r"\bSUB[\s-]?TOTAL\b", summary_text)
        cgst = self._parse_amount_near_keyword(r"\bCGST\b", summary_text)
        sgst = self._parse_amount_near_keyword(r"\bSGST\b", summary_text)
        igst = self._parse_amount_near_keyword(r"\bIGST\b", summary_text)
        tax = self._parse_amount_near_keyword(r"\b(?:TAX|GST|VAT)\b", summary_text)
        total = self._parse_amount_near_keyword(
            r"\bGRAND\s*TOTAL\b|\bAMOUNT\s*(?:DUE|PAYABLE)\b|\bNET\s*AMOUNT\b|(?<!SUB )(?<!SUB-)\bTOTAL\b",
            summary_text
        )
        discount = self._parse_amount_near_keyword(r"\b(?:DISCOUNT|LESS|SAVINGS)\b", summary_text)

        # 8. Payment Method
        payment_method = None
        if re.search(r"UPI|GPay|PhonePe|Paytm", text, re.IGNORECASE):
            payment_method = "UPI"
        elif re.search(r"CASH", text, re.IGNORECASE):
            payment_method = "Cash"
        elif re.search(r"CREDIT|DEBIT|CARD|VISA|MASTER", text, re.IGNORECASE):
            payment_method = "Card"

        # 9. Dynamic Line Item Extraction — driven entirely by the item_lines range
        #    found structurally above, so merchant/footer text can never appear here.
        items = []
        for line in item_lines:
            if self._METADATA_LINE_RE.search(line) or self._SUMMARY_START_RE.search(line):
                continue
            parsed = self._parse_item_line(line)
            if parsed:
                items.append(parsed)

        # Reconcile subtotal against the extracted line-item totals. This repairs
        # common OCR prefix errors such as `7983.00` when the ten actual rows sum
        # to `983.00`. Never fabricate a subtotal when no item totals exist.
        item_sum = round(sum((it.get("total_price") or 0.0) for it in items), 2)
        if item_sum > 0 and (subtotal is None or abs(subtotal - item_sum) > max(2.0, item_sum * 0.05)):
            subtotal = item_sum

        # Rate-aware tax repair. Example OCR: `CGST (2.5%) : %24 58` or
        # `SGST (2.5%) : 724.58`. If a parsed tax is wildly inconsistent with
        # the stated percentage and subtotal, prefer the mathematically expected
        # amount.
        if subtotal is not None:
            for key in ("cgst", "sgst", "igst"):
                value = locals().get(key)
                if value is None:
                    continue
                rate_m = re.search(rf"\b{key.upper()}\b[^\n]{{0,20}}?(\d+(?:\.\d+)?)\s*%", summary_text, re.IGNORECASE)
                if rate_m:
                    expected = round(subtotal * float(rate_m.group(1)) / 100.0, 2)
                    if abs(value - expected) > max(2.0, expected * 0.15):
                        locals()[key] = expected
                        if key == "cgst": cgst = expected
                        elif key == "sgst": sgst = expected
                        else: igst = expected

        computed_tax = tax
        if computed_tax is None and (cgst or sgst or igst):
            computed_tax = (cgst or 0.0) + (sgst or 0.0) + (igst or 0.0)

        computed_total = total
        if computed_total is None and subtotal is not None:
            computed_total = subtotal + (computed_tax or 0.0) - (discount or 0.0)

        # OCR sometimes prefixes a real total with a stray digit/symbol, e.g.
        # `71,202.26` instead of `1,202.26`. If the receipt arithmetic and/or
        # a spelled-out total strongly supports another candidate, repair it.
        if computed_total is not None:
            arithmetic_total = None
            if subtotal is not None:
                arithmetic_total = subtotal + (computed_tax or 0.0) - (discount or 0.0)
            if arithmetic_total is not None and abs(computed_total - arithmetic_total) > 5:
                # If arithmetic_total is corrupted by bad tax OCR, fall back to subtotal/item_sum baseline.
                baseline = arithmetic_total
                if item_sum > 0 and abs(arithmetic_total - item_sum) > item_sum * 0.4:
                    baseline = item_sum

                # Prefer arithmetic only when it is close to the stated amount
                # after removing one leading OCR digit.
                raw_total_candidates = re.findall(r"\b\d[\d,]*\.\d{1,2}\b", summary_text)
                repaired = None
                for raw in raw_total_candidates:
                    try:
                        value = float(raw.replace(",", ""))
                    except ValueError:
                        continue
                    if abs(value - baseline) <= max(2.0, baseline * 0.2):
                        repaired = value
                        break
                
                if repaired is not None:
                    computed_total = repaired
                elif abs(computed_total - baseline) > 50:
                    # Last-resort protection for an obvious OCR prefix (e.g. 71000.16 -> 1000.16)
                    digits = re.sub(r"[^0-9.]", "", str(computed_total))
                    if digits.count(".") == 1:
                        integer, frac = digits.split(".")
                        for i in range(1, min(4, len(integer))):
                            if not integer[i:]: continue
                            candidate = float(integer[i:] + "." + frac)
                            # Check if the stripped number is within 25% of our baseline
                            if abs(candidate - baseline) <= max(2.0, baseline * 0.25):
                                computed_total = candidate
                                break

        return {
            "merchant_name": merchant_name,
            "merchant_address": None,
            "phone": phone,
            "gstin": gstin,
            "receipt_number": receipt_number,
            "invoice_number": receipt_number,
            "receipt_date": receipt_date,
            "receipt_time": receipt_time,
            "currency": currency,
            "subtotal": subtotal,
            "tax": computed_tax,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "discount": discount,
            "total": computed_total,
            "payment_method": payment_method,
            "items": items
        }

    def validate_totals(self, extracted: Dict[str, Any]) -> str | None:
        """Sanity check: subtotal + tax - discount ≈ total."""
        subtotal = extracted.get("subtotal")
        tax = extracted.get("tax")
        discount = extracted.get("discount")
        total = extracted.get("total")

        if total is not None and subtotal is not None:
            expected = subtotal + (tax or 0.0) - (discount or 0.0)
            if abs(expected - total) > 1.0:
                return f"Discrepancy flag: calculated sum ({subtotal:.2f} + {tax or 0:.2f} - {discount or 0:.2f} = {expected:.2f}) differs from stated total ({total:.2f}). Please review."
        return None

extraction_service = ExtractionService()
