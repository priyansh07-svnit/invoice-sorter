import logging
import re
from datetime import date
from enum import Enum
from typing import Annotated

from dateutil import parser as dateutil_parser
from pydantic import BaseModel, BeforeValidator

logger = logging.getLogger(__name__)

_YEAR_RE = re.compile(r'\b(?:19|20)\d{2}\b')
_MONTH_NAME_RE = re.compile(
    r'\b(?:jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|'
    r'aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)\b', re.I
)
_SEPARATOR_RE = re.compile(r'[-/]')


def _parse_date_value(v):
    if v is None or isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            parsed = dateutil_parser.parse(v)
        except (ValueError, OverflowError):
            logger.warning(f"Unparseable date: {v!r}")
            return None

        # Reject dates where dateutil invented missing parts from today's date.
        # Require: a 4-digit year AND (separators like - or / OR a month name).
        years_found = _YEAR_RE.findall(v)
        if not years_found:
            logger.warning(
                f"Incomplete date (missing year): {v!r} → {parsed.date().isoformat()}, rejected"
            )
            return None
        if int(years_found[-1]) != parsed.year:
            logger.warning(
                f"Incomplete date (year mismatch): {v!r} → {parsed.date().isoformat()}, rejected"
            )
            return None
        if not _SEPARATOR_RE.search(v) and not _MONTH_NAME_RE.search(v):
            logger.warning(
                f"Incomplete date (no month/day): {v!r} → {parsed.date().isoformat()}, rejected"
            )
            return None

        return parsed.date()
    return v


ParsedDate = Annotated[date | None, BeforeValidator(_parse_date_value)]


class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"


class ExpenseCategory(str, Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    OFFICE_SUPPLIES = "office_supplies"
    TRAVEL = "travel"
    MEALS = "meals"
    MARKETING = "marketing"
    PROFESSIONAL_SERVICES = "professional_services"
    SUBSCRIPTIONS = "subscriptions"
    UTILITIES = "utilities"
    RENT = "rent"
    INSURANCE = "insurance"
    TAXES = "taxes"
    OTHER = "other"


class Document(BaseModel):
    file_path: str
    document_type: DocumentType = DocumentType.UNKNOWN
    vendor: str | None = None
    amount: float | None = None
    currency: str = "USD"
    date: ParsedDate = None
    invoice_number: str | None = None
    category: ExpenseCategory = ExpenseCategory.OTHER
    description: str | None = None
    raw_text: str | None = None
    confidence: float = 0.0
    needs_review: bool = False

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "document_type": self.document_type.value,
            "vendor": self.vendor,
            "amount": self.amount,
            "currency": self.currency,
            "date": self.date.isoformat() if self.date else None,
            "invoice_number": self.invoice_number,
            "category": self.category.value,
            "description": self.description,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
        }


class ProcessingResult(BaseModel):
    documents: list[Document]
    total_processed: int
    successful: int
    failed: int
    errors: list[str] = []