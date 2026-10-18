import logging
import os
import re
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image

from invoice_sorter.models import Document, DocumentType

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}

_tesseract_cmd = os.environ.get("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


def extract_text_from_pdf(file_path: Path) -> str:
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")

    text = "\n".join(text_parts)

    if not text.strip():
        logger.info(f"No text layer in {file_path.name}, attempting OCR fallback")
        text = _ocr_scanned_pdf(file_path)

    return text


def _ocr_scanned_pdf(file_path: Path) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("pypdfium2 not available for scanned PDF OCR fallback")
        return ""

    text_parts = []
    try:
        pdf = pdfium.PdfDocument(str(file_path))
        for i in range(len(pdf)):
            page = pdf[i]
            image = page.render(scale=2.0).to_pil()
            text = pytesseract.image_to_string(image)
            if text.strip():
                text_parts.append(text)
    except Exception as e:
        logger.error(f"OCR fallback failed for {file_path}: {e}")

    return "\n".join(text_parts)


def extract_text_from_image(file_path: Path) -> str:
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from image {file_path}: {e}")
        return ""


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}:
        return extract_text_from_image(file_path)
    else:
        logger.warning(f"Unsupported file type: {suffix}")
        return ""


def detect_document_type(text: str) -> DocumentType:
    if not text:
        return DocumentType.UNKNOWN

    text_lower = text.lower()

    invoice_keywords = [
        "invoice", "bill to", "ship to", "purchase order", "po number",
        "net 30", "net 15", "due date", "invoice #", "invoice no",
    ]
    receipt_keywords = [
        "receipt", "thank you", "cashier", "transaction", "card ending",
        "auth code", "subtotal", "tax", "total",
    ]

    invoice_score = sum(
        1 for kw in invoice_keywords
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
    )
    receipt_score = sum(
        1 for kw in receipt_keywords
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
    )

    if invoice_score > receipt_score:
        return DocumentType.INVOICE
    elif receipt_score > invoice_score:
        return DocumentType.RECEIPT

    if re.search(r"\binvoice\b", text_lower):
        return DocumentType.INVOICE
    if re.search(r"\breceipt\b", text_lower):
        return DocumentType.RECEIPT

    return DocumentType.UNKNOWN


def process_document(file_path: Path) -> Document:
    text = extract_text(file_path)
    doc_type = detect_document_type(text)

    return Document(
        file_path=str(file_path),
        document_type=doc_type,
        raw_text=text[:5000] if text else None,
    )


def find_documents(input_dir: Path) -> list[Path]:
    documents = []
    for ext in SUPPORTED_EXTENSIONS:
        documents.extend(input_dir.rglob(f"*{ext}"))
    return documents