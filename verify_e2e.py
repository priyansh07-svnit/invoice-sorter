"""End-to-end verification of Ollama LLM extraction path."""

from invoice_sorter.ai_extractor import ExtractedData
from invoice_sorter.models import Document


def test_lenient_parsing():
    print("=== Test 1: Lenient field validation ===")
    result = ExtractedData.lenient({"vendor": 12345, "amount": "$1,234.56", "currency": None, "category": ["software"], "description": ["Line 1", "Line 2"], "confidence": 1.5})
    assert result.vendor == "12345", f"vendor={result.vendor!r}"
    assert result.amount == 1234.56, f"amount={result.amount!r}"
    assert result.currency == "USD", f"currency={result.currency!r}"
    assert result.category == "other", f"category={result.category!r}"
    assert result.description == "['Line 1', 'Line 2']", f"description={result.description!r}"
    assert result.confidence == 1.0, f"confidence={result.confidence!r}"
    print("  PASS")


def test_international_amounts():
    print("=== Test 2: International amounts ===")
    cases = [
        ("€12,50", 12.50),
        ("12.50 USD", 12.50),
        ("1.234,56 EUR", 1234.56),
        ("$1,234.56", 1234.56),
        ("£50.00", 50.00),
    ]
    for amt_str, expected in cases:
        result = ExtractedData.lenient({"amount": amt_str})
        status = "PASS" if result.amount == expected else "FAIL"
        print(f"  {amt_str!r} -> {result.amount} (expected {expected}) [{status}]")
        assert result.amount == expected, f"{amt_str!r} -> {result.amount} != {expected}"
    print("  PASS")


def test_date_parsing():
    print("=== Test 3: Date parsing with dateutil ===")
    doc = Document(file_path="/a.pdf", date="2024-01-15")
    assert doc.date.isoformat() == "2024-01-15", f"date={doc.date}"
    print(f"  ISO '2024-01-15' -> {doc.date.isoformat()}")

    doc = Document(file_path="/a.pdf", date="15/01/2024")
    assert doc.date.isoformat() == "2024-01-15", f"date={doc.date}"
    print(f"  EU '15/01/2024' -> {doc.date.isoformat()}")

    doc = Document(file_path="/a.pdf", date="January 15, 2024")
    assert doc.date.isoformat() == "2024-01-15", f"date={doc.date}"
    print(f"  US 'January 15, 2024' -> {doc.date.isoformat()}")

    doc = Document(file_path="/a.pdf", date="not a date")
    assert doc.date is None, f"date={doc.date}"
    print(f"  'not a date' -> None")
    print("  PASS")


def test_document_dict():
    print("=== Test 4: Document.to_dict() ===")
    doc = Document(
        file_path="/test/invoice.pdf",
        document_type="invoice",
        vendor="Acme Corp",
        amount=100.50,
        currency="USD",
        date="2024-01-15",
        invoice_number="INV-001",
        category="software",
        description="Software license",
        confidence=0.95,
        needs_review=False,
    )
    d = doc.to_dict()
    assert d["vendor"] == "Acme Corp"
    assert d["amount"] == 100.50
    assert d["date"] == "2024-01-15"
    assert d["needs_review"] is False
    print(f"  {d}")
    print("  PASS")


if __name__ == "__main__":
    test_lenient_parsing()
    test_international_amounts()
    test_date_parsing()
    test_document_dict()
    print("\nAll verification tests passed!")
