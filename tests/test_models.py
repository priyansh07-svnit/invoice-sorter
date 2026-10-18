import pytest

from invoice_sorter.models import Document, DocumentType, ExpenseCategory, ProcessingResult


class TestModels:
    def test_document_creation(self):
        doc = Document(
            file_path="/test/invoice.pdf",
            document_type=DocumentType.INVOICE,
            vendor="Test Corp",
            amount=100.50,
            currency="USD",
            date="2024-01-15",
            invoice_number="INV-001",
            category=ExpenseCategory.SOFTWARE,
            description="Software license",
            confidence=0.95,
        )
        assert doc.vendor == "Test Corp"
        assert doc.amount == 100.50
        assert doc.category == ExpenseCategory.SOFTWARE
    
    def test_document_to_dict(self):
        doc = Document(
            file_path="/test/invoice.pdf",
            document_type=DocumentType.RECEIPT,
            vendor="Coffee Shop",
            amount=5.75,
            date="2024-03-10",
            category=ExpenseCategory.MEALS,
        )
        d = doc.to_dict()
        assert d["vendor"] == "Coffee Shop"
        assert d["amount"] == 5.75
        assert d["date"] == "2024-03-10"
        assert d["category"] == "meals"
    
    def test_processing_result(self):
        doc = Document(file_path="/test/invoice.pdf")
        result = ProcessingResult(
            documents=[doc],
            total_processed=1,
            successful=1,
            failed=0,
        )
        assert result.total_processed == 1
        assert result.successful == 1


class TestExpenseCategory:
    def test_all_categories_exist(self):
        categories = [c.value for c in ExpenseCategory]
        assert "software" in categories
        assert "hardware" in categories
        assert "meals" in categories
        assert "other" in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])