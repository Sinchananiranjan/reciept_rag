import re
from typing import List, Tuple, Optional

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.config import settings
from app.utils.file_utils import load_image_with_exif_rotation


class OCREngine:
    """
    Fast, high-recall OCR engine for receipts.

    Design goals:
    - Extract as much receipt text as possible.
    - Preserve receipt/table rows.
    - Avoid extremely slow OCR ensembles.
    - Avoid merging obviously incorrect OCR results.
    - Use Tesseract's confidence information when available.
    """

    _RECEIPT_WORDS = re.compile(
        r"""
        item|items|description|product|products|
        qty|quantity|rate|price|amount|total|
        subtotal|grand\s*total|tax|gst|cgst|sgst|
        invoice|invoice\s*no|receipt|bill|
        date|time|payment|cashier|gstin|
        discount|upi|cash|card|store|shop|
        supermarket|mart|market|phone|address|
        """
        ,
        re.IGNORECASE | re.VERBOSE,
    )

    _MONEY_RE = re.compile(
        r"""
        (?:
            ₹|rs\.?|inr|\$|€|£
        )?
        \s*
        \d[\d,]*
        (?:\.\d{1,2})?
        """
        ,
        re.IGNORECASE | re.VERBOSE,
    )

    _ITEM_ROW_RE = re.compile(
        r"""
        ^\s*
        \d+
        \s+
        .+?
        \s+
        \d+(?:\.\d{1,3})?
        \s+
        \d+(?:[,.]\d{1,2})?
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self):
        self._configure_tesseract()

    # ================================================================
    # TESSERACT CONFIGURATION
    # ================================================================

    def _configure_tesseract(self):
        try:
            import pytesseract

            # Explicit path from .env
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = (
                    settings.TESSERACT_CMD
                )

            try:
                version = pytesseract.get_tesseract_version()
                print(f"[OCR] Tesseract detected: {version}")
                print(
                    f"[OCR] Executable: "
                    f"{pytesseract.pytesseract.tesseract_cmd}"
                )

            except Exception as exc:
                print(
                    f"[OCR] WARNING: Tesseract could not be started: {exc}"
                )

        except ImportError:
            print("[OCR] ERROR: pytesseract is not installed.")

    # ================================================================
    # IMAGE PREPROCESSING
    # ================================================================

    def preprocess_variants(
        self,
        image: Image.Image,
    ) -> List[Image.Image]:
        """
        Create only a few strong OCR variants.

        Previous version:
            up to 8 variants

        New version:
            4 variants

        This is a major speed improvement.
        """

        img = ImageOps.exif_transpose(image).convert("RGB")

        width, height = img.size

        # ------------------------------------------------------------
        # IMPORTANT:
        # Do not enlarge tiny images excessively.
        #
        # Previous code:
        #     2.8x for small images
        #
        # That makes Tesseract extremely slow.
        # ------------------------------------------------------------

        # Prevent aggressive upscaling of already large receipts.
        # This ensures large bold titles remain within Tesseract's optimal font size.
        if width < 600:
            scale = 2.0
        elif width < 1000:
            scale = 1.2
        else:
            scale = 1.0

        new_width = int(width * scale)
        new_height = int(height * scale)

        # Prevent absurdly large images. Tesseract ignores fonts that are too large (e.g. >150px tall).
        max_dimension = 1800

        if new_width > max_dimension or new_height > max_dimension:

            ratio = min(
                max_dimension / new_width,
                max_dimension / new_height,
            )

            new_width = int(new_width * ratio)
            new_height = int(new_height * ratio)

        img = img.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS,
        )

        # ------------------------------------------------------------
        # Variant 1: Original
        # ------------------------------------------------------------

        original = img

        # ------------------------------------------------------------
        # Variant 2: Grayscale + autocontrast
        # ------------------------------------------------------------

        gray = ImageOps.grayscale(img)
        gray = ImageOps.autocontrast(gray, cutoff=1)

        # ------------------------------------------------------------
        # Variant 3: Contrast + sharpen
        # ------------------------------------------------------------

        enhanced = ImageEnhance.Contrast(gray).enhance(1.7)

        enhanced = enhanced.filter(
            ImageFilter.UnsharpMask(
                radius=1.0,
                percent=140,
                threshold=2,
            )
        )

        # ------------------------------------------------------------
        # Variant 4: OTSU/adaptive threshold
        # ------------------------------------------------------------

        threshold = self._opencv_threshold(gray)
        adaptive = self._adaptive_threshold(gray)

        variants = [
            original,
            gray,
            enhanced,
        ]

        if threshold is not None:
            variants.append(threshold)
            
        if adaptive is not None:
            variants.append(adaptive)

        return variants

    # ================================================================
    # OPENCV THRESHOLD
    # ================================================================

    def _opencv_threshold(
        self,
        gray: Image.Image,
    ) -> Optional[Image.Image]:

        try:
            import cv2
            import numpy as np

            arr = np.array(gray)

            # Small blur removes camera noise.
            blurred = cv2.GaussianBlur(
                arr,
                (3, 3),
                0,
            )

            # OTSU automatically determines threshold.
            _, otsu = cv2.threshold(
                blurred,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )

            return Image.fromarray(otsu)

        except Exception:
            return None

    def _adaptive_threshold(
        self,
        gray: Image.Image,
    ) -> Optional[Image.Image]:
        try:
            import cv2
            import numpy as np

            arr = np.array(gray)
            # Slightly larger blur for adaptive thresholding
            blurred = cv2.GaussianBlur(arr, (5, 5), 0)
            
            # Adaptive threshold handles shadows/crumpled receipts much better
            thresh = cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            return Image.fromarray(thresh)
        except Exception:
            return None

    # ================================================================
    # MAIN OCR ENTRY
    # ================================================================

    def extract_text_from_file(
        self,
        file_path: str,
    ) -> Tuple[str, float, bool]:

        print(f"[OCR] Processing: {file_path}")

        images = load_image_with_exif_rotation(file_path)

        if not images:
            print("[OCR] ERROR: Could not load image/PDF.")
            return "", 0.0, False

        page_texts: List[str] = []
        confidences: List[float] = []

        for page_number, image in enumerate(
            images,
            start=1,
        ):

            print(
                f"[OCR] Page {page_number}/{len(images)} "
                f"original_size={image.size}"
            )

            text, confidence = self._run_ocr(
                image
            )

            if text.strip():

                page_texts.append(text.strip())
                confidences.append(confidence)

                print(
                    f"[OCR] Page {page_number}: "
                    f"{len(text)} characters"
                )

                print(
                    f"[OCR] Confidence: "
                    f"{confidence:.2f}"
                )

            else:

                print(
                    f"[OCR] WARNING: "
                    f"Page {page_number} returned no text."
                )

        if not page_texts:

            print(
                "[OCR] ERROR: "
                "No text extracted."
            )

            return "", 0.0, False

        full_text = (
            "\n\n--- PAGE BREAK ---\n\n"
            .join(page_texts)
            .strip()
        )

        print(
            f"[OCR] SUCCESS: "
            f"{len(full_text)} characters extracted"
        )

        return (
            full_text,
            max(confidences or [0.0]),
            True,
        )

    # ================================================================
    # OCR
    # ================================================================

    def _run_ocr(
        self,
        image: Image.Image,
    ) -> Tuple[str, float]:

        try:
            import pytesseract

        except ImportError:

            print(
                "[OCR] ERROR: pytesseract is not installed."
            )

            return "", 0.0

        variants = self.preprocess_variants(image)

        candidates = []

        # ------------------------------------------------------------
        # IMPORTANT SPEED CHANGE
        #
        # Instead of:
        #
        #     8 variants x 5 modes = 40 OCR calls
        #
        # We use:
        #
        #     4 variants x selected modes
        #
        # and stop early when a very good result is found.
        # ------------------------------------------------------------

        configs = [
            "--oem 3 --psm 6",
            "--oem 3 --psm 4",
            "--oem 3 --psm 11",
        ]

        # Prioritize these variants.
        #
        # 0 = original
        # 1 = grayscale
        # 2 = enhanced
        # 3 = threshold
        # 4 = adaptive
        #
        # Grayscale + psm 6 is usually strongest for receipts.

        preferred = [
            (0, "--oem 3 --psm 6"), # original first
            (4, "--oem 3 --psm 6"), # then adaptive
            (1, "--oem 3 --psm 6"), # then grayscale
            (2, "--oem 3 --psm 6"),
            (3, "--oem 3 --psm 6"),
            (1, "--oem 3 --psm 4"),
            (0, "--oem 3 --psm 4"),
            (1, "--oem 3 --psm 11"),
        ]

        # Remove threshold pass if OpenCV wasn't available.
        preferred = [
            (idx, config)
            for idx, config in preferred
            if idx < len(variants)
        ]

        for variant_index, config in preferred:

            variant = variants[variant_index]

            try:

                data = pytesseract.image_to_data(
                    variant,
                    lang="eng",
                    config=config,
                    output_type=pytesseract.Output.DICT,
                )

                text, raw_confidence = (
                    self._text_from_tesseract_data(
                        data
                    )
                )

                text = self._clean_ocr_text(
                    text
                )

                if not text:
                    continue

                quality = self._quality_score(
                    text,
                    raw_confidence,
                )

                candidates.append(
                    (
                        quality,
                        text,
                        raw_confidence,
                        variant_index,
                        config,
                    )
                )

                print(
                    f"[OCR] pass "
                    f"variant={variant_index} "
                    f"config={config} "
                    f"chars={len(text)} "
                    f"confidence={raw_confidence:.1f} "
                    f"score={quality:.1f}"
                )

                # ----------------------------------------------------
                # EARLY EXIT
                #
                # If we already have a strong receipt result,
                # don't waste time running all remaining passes.
                # ----------------------------------------------------

                if (
                    len(text) >= 500
                    and self._receipt_signal(text)
                    and raw_confidence >= 70
                ):
                    print(
                        "[OCR] Strong result found. "
                        "Stopping additional OCR passes."
                    )

                    break

            except Exception as exc:

                print(
                    f"[OCR] Pass failed: "
                    f"variant={variant_index}, "
                    f"config={config}, "
                    f"error={exc}"
                )

        if not candidates:

            print(
                "[OCR] No successful OCR candidates."
            )

            return "", 0.0

        # ------------------------------------------------------------
        # Pick ONE good OCR result.
        #
        # We intentionally do NOT merge multiple OCR outputs.
        #
        # Merging was causing garbage and duplicated/misread lines.
        # ------------------------------------------------------------

        candidates.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        best = candidates[0]

        best_score = best[0]
        best_text = best[1]
        raw_confidence = best[2]
        best_variant = best[3]
        best_config = best[4]

        print(
            f"[OCR] BEST RESULT "
            f"variant={best_variant} "
            f"config={best_config} "
            f"score={best_score:.1f} "
            f"confidence={raw_confidence:.1f} "
            f"chars={len(best_text)}"
        )

        # ------------------------------------------------------------
        # SPLICED HEADER FIX
        # PSM 6 perfectly preserves item tables but drops huge headers.
        # PSM 3 reads huge headers but destroys item tables.
        # We do a quick PSM 3 pass to grab the top lines and prepend them!
        # ------------------------------------------------------------
        try:
            # We use a downscaled version of original image for speed and reliability for large fonts.
            width, height = image.size
            scale = 1000 / width if width > 1000 else 1.0
            header_img = image.resize((int(width * scale), int(height * scale)))
            
            header_text = pytesseract.image_to_string(header_img, config="--oem 3 --psm 3")
            header_lines = [line.strip() for line in header_text.split('\n') if len(line.strip()) >= 3]
            top_header = "\n".join(header_lines[:3])
            
            if top_header:
                print(f"[OCR] Splicing PSM 3 Header:\n{top_header}")
                # Prepend the PSM 3 header to the best PSM 6 text
                best_text = top_header + "\n\n" + best_text
                
        except Exception as e:
            print(f"[OCR] Failed to splice header: {e}")

        confidence = self._final_confidence(
            best_text,
            raw_confidence,
        )

        return best_text, confidence

    # ================================================================
    # TESSERACT DATA -> ROW-PRESERVING TEXT
    # ================================================================

    def _text_from_tesseract_data(
        self,
        data,
    ) -> Tuple[str, float]:

        words = []

        confidences = []

        count = len(
            data.get("text", [])
        )

        for i in range(count):

            text = (
                data["text"][i]
                .strip()
            )

            if not text:
                continue

            try:
                confidence = float(
                    data["conf"][i]
                )
            except Exception:
                confidence = -1

            # Ignore completely useless OCR tokens.
            if confidence < 0:
                continue

            words.append(
                {
                    "text": text,
                    "conf": confidence,
                    "block": data["block_num"][i],
                    "par": data["par_num"][i],
                    "line": data["line_num"][i],
                    "top": data["top"][i],
                    "left": data["left"][i],
                }
            )

            confidences.append(
                confidence
            )

        if not words:
            return "", 0.0

        # ------------------------------------------------------------
        # Group words by Tesseract's detected lines.
        #
        # This is important for:
        #
        # 1 Rice 1 110.00 110.00
        # 2 Milk 1 56.00 56.00
        #
        # rather than one giant text block.
        # ------------------------------------------------------------

        grouped = {}

        for word in words:

            key = (
                word["block"],
                word["par"],
                word["line"],
            )

            grouped.setdefault(
                key,
                []
            ).append(word)

        lines = []

        for _, line_words in grouped.items():

            line_words.sort(
                key=lambda x: x["left"]
            )

            line_text = " ".join(
                word["text"]
                for word in line_words
            )

            if line_text.strip():

                lines.append(
                    (
                        min(
                            word["top"]
                            for word in line_words
                        ),
                        line_text.strip(),
                    )
                )

        # Restore top-to-bottom document order.
        lines.sort(
            key=lambda x: x[0]
        )

        text = "\n".join(
            line[1]
            for line in lines
        )

        average_confidence = (
            sum(confidences)
            / len(confidences)
            if confidences
            else 0.0
        )

        return text, average_confidence

    # ================================================================
    # CLEAN OCR
    # ================================================================

    def _clean_ocr_text(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        cleaned_lines = []

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            # Remove obvious OCR separator garbage.
            if re.fullmatch(
                r"[_=\-|~.]{4,}",
                line,
            ):
                continue

            # Collapse repeated spaces.
            line = re.sub(
                r"[ \t]+",
                " ",
                line,
            )

            # Remove spaces before punctuation.
            line = re.sub(
                r"\s+([,:;.)])",
                r"\1",
                line,
            )

            cleaned_lines.append(
                line
            )

        return "\n".join(
            cleaned_lines
        ).strip()

    # ================================================================
    # RECEIPT SIGNAL
    # ================================================================

    def _receipt_signal(
        self,
        text: str,
    ) -> bool:

        receipt_hits = len(
            self._RECEIPT_WORDS.findall(text)
        )

        money_hits = len(
            self._MONEY_RE.findall(text)
        )

        digit_hits = len(
            re.findall(
                r"\d",
                text,
            )
        )

        return (
            receipt_hits >= 2
            and money_hits >= 3
            and digit_hits >= 8
        )

    # ================================================================
    # QUALITY SCORE
    # ================================================================

    def _quality_score(
        self,
        text: str,
        ocr_confidence: float = 0.0,
    ) -> float:

        if not text:
            return 0.0

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        receipt_hits = len(
            self._RECEIPT_WORDS.findall(text)
        )

        money_hits = len(
            self._MONEY_RE.findall(text)
        )

        item_rows = sum(
            bool(
                self._ITEM_ROW_RE.search(line)
            )
            for line in lines
        )

        digit_hits = len(
            re.findall(
                r"\d",
                text,
            )
        )

        alphabetic_chars = len(
            re.findall(
                r"[A-Za-z]",
                text,
            )
        )

        # Text length is useful but capped.
        length_score = (
            min(
                len(text),
                5000,
            )
            / 25.0
        )

        score = (
            length_score
            + receipt_hits * 20.0
            + min(money_hits, 50) * 8.0
            + min(item_rows, 30) * 20.0
            + min(digit_hits, 200) * 0.15
            + min(alphabetic_chars, 2500) * 0.02
            + ocr_confidence * 1.5
        )

        return score

    # ================================================================
    # FINAL CONFIDENCE
    # ================================================================

    def _final_confidence(
        self,
        text: str,
        ocr_confidence: float,
    ) -> float:

        if not text:
            return 0.0

        # Tesseract's actual word confidence is much more useful
        # than the old artificial score/350 formula.

        confidence = (
            ocr_confidence / 100.0
        )

        # Small bonus for strong receipt structure.
        if self._receipt_signal(text):
            confidence += 0.05

        return max(
            0.0,
            min(
                confidence,
                0.99,
            ),
        )


ocr_service = OCREngine()