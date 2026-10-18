import json
import logging
import re

import ollama
from pydantic import BaseModel, ValidationError

from invoice_sorter.models import Document, ExpenseCategory

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an expert at extracting structured data from invoices and receipts.
Extract the following information from the document text and return ONLY a valid JSON object:

{
  "vendor": "Company or person name who issued the document",
  "amount": 123.45,
  "currency": "USD",
  "date": "2024-01-15",
  "invoice_number": "INV-2024-001",
  "category": "software",
  "description": "Brief description of what this is for",
  "confidence": 0.95
}

Categories must be one of: software, hardware, office_supplies, travel,
    meals, marketing, professional_services, subscriptions, utilities, rent,
    insurance, taxes, other

Rules:
- Amount should be a number (float), not a string
- Date must be in YYYY-MM-DD format
- If information is not found, use null
- Confidence should be 0.0 to 1.0 based on how certain you are
- Return ONLY the JSON object, no markdown, no explanation

Document text:
{text}
"""


class ExtractedData(BaseModel):
    vendor: str | None = None
    amount: float | None = None
    currency: str = "USD"
    date: str | None = None
    invoice_number: str | None = None
    category: str = "other"
    description: str | None = None
    confidence: float = 0.0

    @classmethod
    def lenient(cls, data: dict) -> "ExtractedData":
        """Coerce common model mistakes into valid types, never raising."""
        coerced = dict(data)

        # Vendor: must be string or None
        v = coerced.get("vendor")
        if v is not None and not isinstance(v, str):
            coerced["vendor"] = str(v)

        # Amount: strip any currency symbol or code, handle decimal comma
        amt = coerced.get("amount")
        if amt is not None:
            try:
                if isinstance(amt, str):
                    cleaned = amt.strip()
                    # Remove currency symbols
                    cleaned = re.sub(r'[€$£¥₹₽₩₪₫]', '', cleaned)
                    # Remove currency codes (USD, EUR, GBP, etc.)
                    currency_codes = r'\b(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|RUB|KRW)\b'
                    cleaned = re.sub(currency_codes, '', cleaned, flags=re.IGNORECASE)
                    cleaned = cleaned.replace(' ', '')
                    if ',' in cleaned and '.' in cleaned:
                        # Both present: determine which is decimal separator
                        last_comma = cleaned.rfind(',')
                        last_dot = cleaned.rfind('.')
                        if last_comma > last_dot:
                            # Comma is decimal (EU: 1.234,56) → remove dots, replace comma with dot
                            cleaned = cleaned.replace('.', '').replace(',', '.')
                        else:
                            # Dot is decimal (US: 1,234.56) → remove commas
                            cleaned = cleaned.replace(',', '')
                    elif ',' in cleaned and '.' not in cleaned:
                        parts = cleaned.split(',')
                        if len(parts) == 2 and len(parts[1]) <= 2:
                            cleaned = parts[0] + '.' + parts[1]
                        else:
                            cleaned = cleaned.replace(',', '')
                    coerced["amount"] = float(cleaned)
                    # Note: "1.250" with only a dot is read as 1.25 (US decimal).
                    # EU users writing "1.250" for one-thousand-two-hundred-fifty
                    # would need to write "1250" or "1.250,00" to be unambiguous.
                else:
                    coerced["amount"] = float(amt)
            except (ValueError, TypeError):
                coerced["amount"] = None

        # Currency: default to USD if null or empty
        if not coerced.get("currency"):
            coerced["currency"] = "USD"

        # Invoice number: must be string or None
        inv = coerced.get("invoice_number")
        if inv is not None and not isinstance(inv, str):
            coerced["invoice_number"] = str(inv)

        # Description: must be string or None
        desc = coerced.get("description")
        if desc is not None and not isinstance(desc, str):
            coerced["description"] = str(desc)

        # Category: default to other if invalid
        cat = coerced.get("category")
        if cat is not None and not isinstance(cat, str):
            coerced["category"] = "other"

        # Confidence: clamp to 0-1. Default missing confidence to 0.5 so a
        # document with vendor+amount but no confidence is still "successful".
        conf = coerced.get("confidence")
        if conf is not None:
            try:
                coerced["confidence"] = max(0.0, min(1.0, float(conf)))
            except (ValueError, TypeError):
                coerced["confidence"] = 0.5
        else:
            coerced["confidence"] = 0.5

        try:
            return cls(**coerced)
        except ValidationError:
            return cls()


class AIExtractor:
    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=host)

    def extract(self, document: Document) -> Document:
        if not document.raw_text:
            logger.warning(f"No text to extract from: {document.file_path}")
            document.confidence = 0.0
            document.needs_review = True
            return document

        prompt = EXTRACTION_PROMPT.replace("{text}", document.raw_text)

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 500}
            )

            if isinstance(response, dict):
                response_text = response.get("response", "")
            else:
                response_text = getattr(response, "response", "")

            extracted = self._parse_response(response_text)
            self._apply_extracted_data(document, extracted)

            # If no fields were extracted, flag for review
            if not document.vendor and document.amount is None:
                document.needs_review = True

        except Exception as e:
            logger.error(f"Error extracting data from {document.file_path}: {e}")
            document.confidence = 0.0
            document.needs_review = True

        return document

    def _parse_response(self, response: str) -> ExtractedData:
        # Use raw_decode from the first '{' instead of a greedy regex, so
        # multiple JSON objects in the response don't get swallowed into one
        # invalid blob.
        decoder = json.JSONDecoder()
        idx = response.find('{')
        if idx == -1:
            logger.warning(f"No JSON object found in response: {response[:200]}")
            return ExtractedData()

        try:
            data, _ = decoder.raw_decode(response[idx:])
            return ExtractedData.lenient(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse JSON: {e}")
            return ExtractedData()

    def _apply_extracted_data(self, document: Document, extracted: ExtractedData):
        document.vendor = extracted.vendor
        document.amount = extracted.amount
        document.currency = extracted.currency
        document.date = extracted.date
        document.invoice_number = extracted.invoice_number

        # Strip whitespace before matching category ("Software " → "software")
        cat = extracted.category.strip().lower() if extracted.category else "other"
        try:
            document.category = ExpenseCategory(cat)
        except ValueError:
            document.category = ExpenseCategory.OTHER

        document.description = extracted.description
        document.confidence = max(0.0, min(1.0, extracted.confidence))


def create_extractor(
    model: str = "llama3.2:3b", host: str = "http://localhost:11434"
) -> AIExtractor:
    return AIExtractor(model=model, host=host)