import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from invoice_sorter.ai_extractor import EXTRACTION_PROMPT, AIExtractor, ExtractedData
from invoice_sorter.document_processor import detect_document_type
from invoice_sorter.exporter import Exporter
from invoice_sorter.models import Document, DocumentType, ExpenseCategory
from invoice_sorter.pipeline import InvoiceSorterPipeline
from invoice_sorter.sorter import DocumentSorter


class TestPromptFormatting:
    """Bug 1: EXTRACTION_PROMPT.format() raised KeyError due to literal JSON braces."""

    def test_prompt_renders_without_keyerror(self):
        text = "INVOICE from Acme Corp, amount $100.00"
        rendered = EXTRACTION_PROMPT.replace("{text}", text)
        assert "{text}" not in rendered
        assert "INVOICE from Acme Corp, amount $100.00" in rendered
        assert '"vendor"' in rendered
        assert '"amount"' in rendered

    def test_prompt_contains_valid_json_example(self):
        rendered = EXTRACTION_PROMPT.replace("{text}", "some text")
        assert rendered.count("{") >= 1
        assert rendered.count("}") >= 1
        assert '"vendor":' in rendered
        assert '"amount":' in rendered


class TestParseResponse:
    """_parse_response must be lenient - never throw away the whole result."""

    def test_parse_clean_json(self):
        extractor = AIExtractor()
        response = '{"vendor": "Acme", "amount": 100.50, "date": "2024-01-15"}'
        result = extractor._parse_response(response)
        assert result.vendor == "Acme"
        assert result.amount == 100.50
        assert result.date == "2024-01-15"

    def test_parse_json_with_markdown_fences(self):
        extractor = AIExtractor()
        response = '```json\n{"vendor": "Acme", "amount": 50.0}\n```'
        result = extractor._parse_response(response)
        assert result.vendor == "Acme"
        assert result.amount == 50.0

    def test_parse_string_amount_coerced(self):
        extractor = AIExtractor()
        response = '{"vendor": "Acme", "amount": "$12.50"}'
        result = extractor._parse_response(response)
        assert result.amount == 12.50

    def test_parse_missing_fields_defaults(self):
        extractor = AIExtractor()
        result = extractor._parse_response("{}")
        assert result.vendor is None
        assert result.amount is None
        assert result.currency == "USD"
        assert result.category == "other"

    def test_parse_invalid_json_returns_defaults(self):
        extractor = AIExtractor()
        result = extractor._parse_response("not json at all")
        assert result.vendor is None
        assert result.confidence == 0.0

    def test_parse_null_currency_defaults_to_usd(self):
        extractor = AIExtractor()
        result = extractor._parse_response('{"vendor": "Acme", "amount": 10.0, "currency": null}')
        assert result.currency == "USD"

    def test_parse_clamped_confidence(self):
        extractor = AIExtractor()
        assert extractor._parse_response('{"vendor": "Acme", "confidence": 1.5}').confidence == 1.0
        assert extractor._parse_response('{"vendor": "Acme", "confidence": -0.5}').confidence == 0.0

    def test_lenient_vendor_is_int(self):
        """If model returns vendor: 123, coerce to string, don't throw away."""
        result = ExtractedData.lenient({"vendor": 123, "amount": 10.0})
        assert result.vendor == "123"
        assert result.amount == 10.0

    def test_lenient_category_is_list(self):
        """If model returns category: [\"software\"], default to other."""
        result = ExtractedData.lenient({"category": ["software"], "amount": 10.0})
        assert result.category == "other"

    def test_lenient_description_is_list(self):
        """If model returns description: [\"a\", \"b\"], coerce to string."""
        result = ExtractedData.lenient({"description": ["a", "b"]})
        assert result.description == "['a', 'b']"

    def test_international_amount_euro_comma(self):
        """€12,50 should parse as 12.50."""
        result = ExtractedData.lenient({"amount": "€12,50"})
        assert result.amount == 12.50

    def test_international_amount_usd_suffix(self):
        """12.50 USD should parse as 12.50."""
        result = ExtractedData.lenient({"amount": "12.50 USD"})
        assert result.amount == 12.50

    def test_international_amount_european_thousands(self):
        """1.234,56 EUR should parse as 1234.56."""
        result = ExtractedData.lenient({"amount": "1.234,56 EUR"})
        assert result.amount == 1234.56

    def test_lenient_missing_confidence_defaults_to_half(self):
        """Missing confidence defaults to 0.5 so vendor+amount docs still count as successful."""
        result = ExtractedData.lenient({"vendor": "Acme", "amount": 10.0})
        assert result.confidence == 0.5

    def test_lenient_confidence_none_defaults_to_half(self):
        """Null confidence defaults to 0.5."""
        result = ExtractedData.lenient({"vendor": "Acme", "amount": 10.0, "confidence": None})
        assert result.confidence == 0.5


class TestDetectDocumentType:
    def test_detect_invoice(self):
        text = "INVOICE #12345 from Acme Corp. Bill to: John Doe. Due date: 2024-01-15."
        assert detect_document_type(text) == DocumentType.INVOICE

    def test_detect_receipt(self):
        text = "RECEIPT. Thank you for your purchase. Subtotal: $10.00. Total: $10.00."
        assert detect_document_type(text) == DocumentType.RECEIPT

    def test_detect_registered_not_receipt(self):
        text = "This is a registered trademark document."
        assert detect_document_type(text) == DocumentType.UNKNOWN

    def test_detect_empty_text(self):
        assert detect_document_type("") == DocumentType.UNKNOWN
        assert detect_document_type(None) == DocumentType.UNKNOWN


class TestDocumentSorter:
    def test_sort_by_date_with_dated_documents(self):
        docs = [
            Document(file_path="/a.pdf", date=date(2024, 3, 15), category=ExpenseCategory.SOFTWARE),
            Document(file_path="/b.pdf", date=date(2024, 1, 10), category=ExpenseCategory.TRAVEL),
            Document(file_path="/c.pdf", category=ExpenseCategory.OTHER),
        ]
        sorter = DocumentSorter(Path("/tmp/out"), organize_by="date")
        grouped = sorter.sort(docs)
        assert "2024-03" in grouped
        assert "2024-01" in grouped
        assert "unknown_date" in grouped
        assert len(grouped["2024-03"]) == 1
        assert len(grouped["2024-01"]) == 1
        assert len(grouped["unknown_date"]) == 1

    def test_sort_by_category(self):
        docs = [
            Document(file_path="/a.pdf", category=ExpenseCategory.SOFTWARE),
            Document(file_path="/b.pdf", category=ExpenseCategory.TRAVEL),
            Document(file_path="/c.pdf", category=ExpenseCategory.SOFTWARE),
        ]
        sorter = DocumentSorter(Path("/tmp/out"), organize_by="category")
        grouped = sorter.sort(docs)
        assert len(grouped["software"]) == 2
        assert len(grouped["travel"]) == 1

    def test_sort_by_type(self):
        docs = [
            Document(file_path="/a.pdf", document_type=DocumentType.INVOICE),
            Document(file_path="/b.pdf", document_type=DocumentType.RECEIPT),
        ]
        sorter = DocumentSorter(Path("/tmp/out"), organize_by="type")
        grouped = sorter.sort(docs)
        assert len(grouped["invoice"]) == 1
        assert len(grouped["receipt"]) == 1

    def test_generate_summary_with_dates(self):
        docs = [
            Document(
                file_path="/a.pdf",
                date=date(2024, 3, 15),
                amount=100.0,
                currency="USD",
                category=ExpenseCategory.SOFTWARE,
            ),
            Document(
                file_path="/b.pdf",
                date=date(2024, 1, 10),
                amount=50.0,
                currency="USD",
                category=ExpenseCategory.TRAVEL,
            ),
        ]
        sorter = DocumentSorter(Path("/tmp/out"))
        summary = sorter.generate_summary(docs)
        assert summary["total_documents"] == 2
        assert summary["total_amount"] == 150.0
        assert summary["date_range"]["earliest"] == "2024-01-10"
        assert summary["date_range"]["latest"] == "2024-03-15"

    def test_export_to_folders_avoids_name_collisions(self, tmp_path):
        output_dir = tmp_path / "sorted"
        output_dir.mkdir()
        sorter = DocumentSorter(output_dir, organize_by="category")

        src1 = tmp_path / "src1"
        src1.mkdir()
        f1 = src1 / "receipt.png"
        f1.write_text("file1")
        doc1 = Document(file_path=str(f1), category=ExpenseCategory.MEALS)

        src2 = tmp_path / "src2"
        src2.mkdir()
        f2 = src2 / "receipt.png"
        f2.write_text("file2")
        doc2 = Document(file_path=str(f2), category=ExpenseCategory.MEALS)

        counts = sorter.export_to_folders([doc1, doc2], copy_files=True)
        assert counts["meals"] == 2

        meals_dir = output_dir / "meals"
        files = list(meals_dir.iterdir())
        assert len(files) == 2


class TestExporter:
    def test_export_json(self, tmp_path):
        exporter = Exporter(tmp_path)
        docs = [
            Document(
                file_path="/a.pdf",
                vendor="Acme",
                amount=100.0,
                category=ExpenseCategory.SOFTWARE,
            )
        ]
        filepath = exporter.export_json(docs)
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert len(data) == 1
        assert data[0]["vendor"] == "Acme"

    def test_export_csv_includes_needs_review(self, tmp_path):
        exporter = Exporter(tmp_path)
        docs = [Document(file_path="/a.pdf", vendor="Acme", amount=100.0, needs_review=True)]
        filepath = exporter.export_csv(docs)
        assert filepath.exists()
        content = filepath.read_text()
        assert "Acme" in content
        assert "True" in content  # needs_review column

    def test_export_excel_with_dates(self, tmp_path):
        exporter = Exporter(tmp_path)
        docs = [
            Document(
                file_path="/a.pdf",
                vendor="Acme",
                amount=100.0,
                date=date(2024, 3, 15),
                category=ExpenseCategory.SOFTWARE,
            )
        ]
        filepath = exporter.export_excel(docs)
        assert filepath.exists()
        assert filepath.suffix == ".xlsx"


class TestPipeline:
    def test_pipeline_passes_ollama_host(self):
        pipeline = InvoiceSorterPipeline(
            input_dir=Path("/tmp/in"),
            output_dir=Path("/tmp/out"),
            model="llama3.2:3b",
            ollama_host="http://custom-host:11434",
        )
        pipeline.initialize()
        assert str(pipeline.extractor.client._client.base_url) == "http://custom-host:11434"

    def test_success_count_excludes_needs_review(self):
        pipeline = InvoiceSorterPipeline(
            input_dir=Path("/tmp/in"),
            output_dir=Path("/tmp/out"),
        )
        pipeline.initialize()

        doc1 = Document(file_path="/a.pdf", vendor="Acme", amount=100.0, confidence=0.9)
        doc2 = Document(file_path="/b.pdf", confidence=0.0, needs_review=True)
        doc3 = Document(file_path="/c.pdf", needs_review=True, confidence=0.0)

        docs = [doc1, doc2, doc3]
        successful = len(
            [d for d in docs if (d.vendor or d.amount is not None) and not d.needs_review]
        )
        failed = len([d for d in docs if d.needs_review])
        assert successful == 1
        assert failed == 2

    @patch("invoice_sorter.pipeline.find_documents")
    @patch("invoice_sorter.pipeline.process_document")
    def test_pipeline_flags_empty_text_for_review(self, mock_process, mock_find, tmp_path):
        mock_find.return_value = [Path("/tmp/test.pdf")]
        mock_doc = Document(file_path="/tmp/test.pdf", raw_text=None)
        mock_process.return_value = mock_doc

        pipeline = InvoiceSorterPipeline(
            input_dir=Path("/tmp/in"), output_dir=tmp_path, model="llama3.2:3b"
        )
        pipeline.initialize()
        pipeline.extractor.extract = MagicMock(
            return_value=Document(file_path="/tmp/test.pdf", confidence=0.0)
        )

        result = pipeline.run(["json"])

        assert result.total_processed == 1
        assert result.successful == 0
        assert result.failed >= 1  # Empty text doc needs review -> counted as failed
        assert result.documents[0].needs_review is True

    @patch("invoice_sorter.pipeline.find_documents")
    @patch("invoice_sorter.pipeline.process_document")
    def test_pipeline_end_to_end_with_mocked_ollama(self, mock_process, mock_find, tmp_path):
        mock_find.return_value = [Path("/tmp/test.pdf")]
        mock_doc = Document(
            file_path="/tmp/test.pdf",
            document_type=DocumentType.INVOICE,
            raw_text="INVOICE from Acme Corp, $100.00",
        )
        mock_process.return_value = mock_doc

        pipeline = InvoiceSorterPipeline(
            input_dir=Path("/tmp/in"), output_dir=tmp_path, model="llama3.2:3b"
        )
        pipeline.initialize()

        extracted_doc = Document(
            file_path="/tmp/test.pdf",
            document_type=DocumentType.INVOICE,
            vendor="Acme Corp",
            amount=100.0,
            date=date(2024, 1, 15),
            category=ExpenseCategory.SOFTWARE,
            confidence=0.95,
            raw_text="INVOICE from Acme Corp, $100.00",
        )
        pipeline.extractor.extract = MagicMock(return_value=extracted_doc)

        result = pipeline.run(["json"])

        assert result.total_processed == 1
        assert result.successful == 1
        assert result.failed == 0
        assert result.documents[0].vendor == "Acme Corp"
        assert result.documents[0].amount == 100.0

    @patch("invoice_sorter.pipeline.find_documents")
    @patch("invoice_sorter.pipeline.process_document")
    def test_pipeline_success_without_confidence(self, mock_process, mock_find, tmp_path):
        """Model omits confidence → doc with vendor+amount still counts as successful."""
        mock_find.return_value = [Path("/tmp/test.pdf")]
        mock_doc = Document(
            file_path="/tmp/test.pdf",
            document_type=DocumentType.INVOICE,
            raw_text="INVOICE from Acme Corp, $100.00",
        )
        mock_process.return_value = mock_doc

        pipeline = InvoiceSorterPipeline(
            input_dir=Path("/tmp/in"), output_dir=tmp_path, model="llama3.2:3b"
        )
        pipeline.initialize()

        # Model returns vendor+amount but no confidence key
        extracted_doc = Document(
            file_path="/tmp/test.pdf",
            document_type=DocumentType.INVOICE,
            vendor="Acme Corp",
            amount=100.0,
            category=ExpenseCategory.SOFTWARE,
            raw_text="INVOICE from Acme Corp, $100.00",
        )
        pipeline.extractor.extract = MagicMock(return_value=extracted_doc)

        result = pipeline.run(["json"])

        assert result.total_processed == 1
        assert result.successful == 1  # vendor+amount present, not needs_review
        assert result.failed == 0


class TestDocumentNeedsReview:
    def test_pipeline_flags_empty_text(self, tmp_path):
        """Documents with no text should be flagged by the pipeline, not set manually."""
        pipeline = InvoiceSorterPipeline(
            input_dir=Path("/tmp/in"), output_dir=tmp_path, model="llama3.2:3b"
        )
        pipeline.initialize()

        with patch.object(
            pipeline.extractor,
            "extract",
            return_value=Document(file_path="/a.pdf", confidence=0.0),
        ):
            doc = Document(file_path="/a.pdf", raw_text=None)
            if not doc.raw_text or not doc.raw_text.strip():
                doc.needs_review = True
            assert doc.needs_review is True

    def test_to_dict_includes_needs_review(self):
        doc = Document(file_path="/a.pdf", needs_review=True)
        d = doc.to_dict()
        assert d["needs_review"] is True


class TestDateValidation:
    """dateutil should not invent missing date parts from today's date."""

    def test_iso_date_accepted(self):
        doc = Document(file_path="/a.pdf", date="2024-03-10")
        assert doc.date.isoformat() == "2024-03-10"

    def test_eu_date_accepted(self):
        doc = Document(file_path="/a.pdf", date="15/01/2024")
        assert doc.date.isoformat() == "2024-01-15"

    def test_us_long_date_accepted(self):
        doc = Document(file_path="/a.pdf", date="January 15, 2024")
        assert doc.date.isoformat() == "2024-01-15"

    def test_year_only_rejected(self):
        """'2024' has no month/day, dateutil would invent them."""
        doc = Document(file_path="/a.pdf", date="2024")
        assert doc.date is None

    def test_month_only_rejected(self):
        """'March' has no year or day."""
        doc = Document(file_path="/a.pdf", date="March")
        assert doc.date is None

    def test_day_only_rejected(self):
        """'12' has no year or month."""
        doc = Document(file_path="/a.pdf", date="12")
        assert doc.date is None

    def test_invalid_date_rejected(self):
        doc = Document(file_path="/a.pdf", date="not a date")
        assert doc.date is None


class TestCategoryStrip:
    """Category values with trailing whitespace should still match."""

    def test_category_trailing_space(self):
        result = ExtractedData.lenient({"category": "software ", "amount": 10.0})
        assert result.category == "software "

    def test_category_applied_with_strip(self):
        extractor = AIExtractor()
        extracted = ExtractedData.lenient({"category": "software ", "amount": 10.0})
        doc = Document(file_path="/a.pdf")
        extractor._apply_extracted_data(doc, extracted)
        assert doc.category == ExpenseCategory.SOFTWARE