import os
import hashlib
import logging
from typing import List, Tuple

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
    ".heic",
}

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


# ============================================================
# FILE VALIDATION
# ============================================================

def validate_file(
    filename: str,
    file_size: int
) -> Tuple[bool, str]:
    """
    Validate an uploaded receipt file.

    Supported:
        JPG
        JPEG
        PNG
        WEBP
        PDF
        HEIC

    Returns:
        (True, "") when valid
        (False, error_message) when invalid
    """

    if not filename:
        return False, "Uploaded file has no filename."

    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(
            extension.upper().replace(".", "")
            for extension in sorted(ALLOWED_EXTENSIONS)
        )

        return False, (
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {allowed}."
        )

    if file_size <= 0:
        return False, "Uploaded file is empty."

    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)

        return False, (
            f"File size exceeds the 25 MB limit "
            f"(received {size_mb:.2f} MB)."
        )

    return True, ""


# ============================================================
# FILE HASH
# ============================================================

def compute_sha256(file_bytes: bytes) -> str:
    """
    Calculate SHA-256 hash of the uploaded file.

    Used for:
        - duplicate detection
        - file integrity
        - identifying identical uploads
    """

    return hashlib.sha256(file_bytes).hexdigest()


# ============================================================
# PDF → IMAGES
# ============================================================

def convert_pdf_to_images(
    pdf_path: str
) -> List[Image.Image]:
    """
    Convert every page of a PDF into PIL RGB images.

    Strategy:

        PDF
         ↓
        pdf2image
         ↓
        if failed
         ↓
        PyMuPDF
         ↓
        PIL RGB images

    Returns:
        One PIL Image per PDF page.

    Raises:
        FileNotFoundError
        RuntimeError
    """

    if not pdf_path:
        raise ValueError("PDF path is empty.")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"PDF file does not exist: {pdf_path}"
        )

    # --------------------------------------------------------
    # METHOD 1: pdf2image
    # --------------------------------------------------------

    try:
        from pdf2image import convert_from_path

        logger.info(
            "Attempting PDF conversion with pdf2image: %s",
            pdf_path
        )

        images = convert_from_path(
            pdf_path,
            dpi=200,
            fmt="RGB",
        )

        if images:
            processed_images = []

            for image in images:
                image = ImageOps.exif_transpose(image)
                image = image.convert("RGB")

                processed_images.append(image)

            logger.info(
                "PDF converted successfully with pdf2image: "
                "%d page(s)",
                len(processed_images)
            )

            return processed_images

    except Exception as exc:
        logger.warning(
            "pdf2image failed for '%s': %s",
            pdf_path,
            exc
        )

    # --------------------------------------------------------
    # METHOD 2: PyMuPDF
    # --------------------------------------------------------

    try:
        import fitz

        logger.info(
            "Attempting PDF conversion with PyMuPDF: %s",
            pdf_path
        )

        images: List[Image.Image] = []

        with fitz.open(pdf_path) as document:

            if document.page_count == 0:
                raise RuntimeError(
                    "PDF contains no pages."
                )

            for page_number, page in enumerate(document):

                # Approximately 144–150 DPI.
                # 2x gives substantially better OCR quality
                # than rendering at the default resolution.
                matrix = fitz.Matrix(2.0, 2.0)

                pixmap = page.get_pixmap(
                    matrix=matrix,
                    alpha=False
                )

                image = Image.frombytes(
                    "RGB",
                    [
                        pixmap.width,
                        pixmap.height
                    ],
                    pixmap.samples
                )

                images.append(image)

                logger.debug(
                    "Rendered PDF page %d/%d",
                    page_number + 1,
                    document.page_count
                )

        if images:

            logger.info(
                "PDF converted successfully with PyMuPDF: "
                "%d page(s)",
                len(images)
            )

            return images

    except Exception as exc:

        logger.exception(
            "PyMuPDF failed for '%s'",
            pdf_path
        )

        raise RuntimeError(
            f"Unable to read PDF "
            f"'{os.path.basename(pdf_path)}'. "
            f"Both PDF conversion methods failed. "
            f"Original error: {exc}"
        ) from exc

    # --------------------------------------------------------
    # NO PDF ENGINE WORKED
    # --------------------------------------------------------

    raise RuntimeError(
        f"Unable to convert PDF "
        f"'{os.path.basename(pdf_path)}'. "
        f"No pages were extracted."
    )


# ============================================================
# IMAGE LOADING
# ============================================================

def load_image_with_exif_rotation(
    file_path: str
) -> List[Image.Image]:
    """
    Load a receipt file into PIL RGB images.

    Supported:

        JPG
        JPEG
        PNG
        WEBP
        HEIC
        PDF

    Behavior:

        Image
          ↓
        EXIF rotation
          ↓
        RGB image

        PDF
          ↓
        one RGB image per page

    Returns:
        List[Image.Image]
    """

    if not file_path:
        raise ValueError(
            "Receipt file path is empty."
        )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Receipt file does not exist: {file_path}"
        )

    ext = os.path.splitext(
        file_path.lower()
    )[1]

    logger.info(
        "Loading receipt file: %s",
        file_path
    )

    # ========================================================
    # PDF
    # ========================================================

    if ext == ".pdf":

        images = convert_pdf_to_images(
            file_path
        )

        if not images:
            raise RuntimeError(
                f"No pages could be extracted from "
                f"'{os.path.basename(file_path)}'."
            )

        return images

    # ========================================================
    # HEIC
    # ========================================================

    if ext == ".heic":

        try:
            import pillow_heif

            pillow_heif.register_heif_opener()

            logger.info(
                "HEIC support enabled using pillow-heif."
            )

        except ImportError as exc:

            raise RuntimeError(
                "HEIC receipt detected, but "
                "pillow-heif is not installed. "
                "Install it with:\n\n"
                "pip install pillow-heif"
            ) from exc

    # ========================================================
    # NORMAL IMAGE
    # ========================================================

    try:

        # ----------------------------------------------------
        # First pass: verify that PIL can decode the file.
        # ----------------------------------------------------

        with Image.open(file_path) as source:

            source.verify()

        # ----------------------------------------------------
        # Second pass: reopen because verify() invalidates
        # the image object.
        # ----------------------------------------------------

        with Image.open(file_path) as source:

            logger.info(
                "Original image format: %s",
                source.format
            )

            logger.info(
                "Original image size: %dx%d",
                source.width,
                source.height
            )

            # Automatically correct EXIF orientation.
            image = ImageOps.exif_transpose(
                source
            )

            # Convert every supported image to RGB.
            image = image.convert("RGB")

            # Detach from the file handle.
            image = image.copy()

        logger.info(
            "Receipt image loaded successfully: "
            "%dx%d",
            image.width,
            image.height
        )

        return [image]

    except FileNotFoundError:

        raise

    except Exception as exc:

        logger.exception(
            "Unable to open receipt image '%s'",
            file_path
        )

        raise RuntimeError(
            f"Unable to read receipt image "
            f"'{os.path.basename(file_path)}': {exc}"
        ) from exc


# ============================================================
# GENERIC RECEIPT LOADER
# ============================================================

def load_receipt_images(
    file_path: str
) -> List[Image.Image]:
    """
    Public helper for the OCR pipeline.

    This is the recommended function to call from
    ocr_service.py.

    It supports:

        JPG
        JPEG
        PNG
        WEBP
        HEIC
        PDF

    Returns:
        List of RGB PIL images.
    """

    if not file_path:
        raise ValueError(
            "Receipt file path is required."
        )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Receipt file not found: {file_path}"
        )

    images = load_image_with_exif_rotation(
        file_path
    )

    if not images:
        raise RuntimeError(
            f"Receipt file could not be converted "
            f"into an image: {os.path.basename(file_path)}"
        )

    # Make sure every returned image is RGB.
    normalized_images = []

    for index, image in enumerate(images):

        if image is None:
            logger.warning(
                "Page/image %d returned None.",
                index + 1
            )
            continue

        if image.mode != "RGB":
            image = image.convert("RGB")

        normalized_images.append(image)

    if not normalized_images:
        raise RuntimeError(
            f"No readable image pages found in "
            f"'{os.path.basename(file_path)}'."
        )

    logger.info(
        "Receipt loaded: %d image/page(s)",
        len(normalized_images)
    )

    return normalized_images