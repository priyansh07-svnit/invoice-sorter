import logging
from pathlib import Path

from invoice_sorter.ai_extractor import AIExtractor, create_extractor
from invoice_sorter.document_processor import find_documents, process_document
from invoice_sorter.exporter import Exporter, export_all
from invoice_sorter.models import ProcessingResult
from invoice_sorter.sorter import DocumentSorter

logger = logging.getLogger(__name__)


class InvoiceSorterPipeline:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        model: str = "llama3.2:3b",
        organize_by: str = "category",
        ollama_host: str = "http://localhost:11434",
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.model = model
        self.organize_by = organize_by
        self.ollama_host = ollama_host
        self.extractor: AIExtractor | None = None
        self.sorter = DocumentSorter(output_dir / "sorted", organize_by)
        self.exporter = Exporter(output_dir)

    def initialize(self):
        self.extractor = create_extractor(self.model, host=self.ollama_host)
        logger.info(f"Initialized with model: {self.model} at {self.ollama_host}")

    def run(self, export_formats: list[str] | None = None) -> ProcessingResult:
        if not self.extractor:
            self.initialize()

        logger.info(f"Scanning for documents in: {self.input_dir}")
        doc_paths = find_documents(self.input_dir)
        logger.info(f"Found {len(doc_paths)} documents")

        documents = []
        errors = []

        for i, path in enumerate(doc_paths, 1):
            try:
                logger.info(f"Processing [{i}/{len(doc_paths)}]: {path.name}")
                doc = process_document(path)

                if not doc.raw_text or not doc.raw_text.strip():
                    doc.needs_review = True
                    logger.warning(f"No text extracted from {path.name}, flagging for review")

                doc = self.extractor.extract(doc)

                if doc.confidence == 0.0 and not doc.vendor and doc.amount is None:
                    doc.needs_review = True
                    logger.warning(f"No data extracted from {path.name}, flagging for review")

                documents.append(doc)
            except Exception as e:
                error_msg = f"Failed to process {path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info("Sorting documents...")
        self.sorter.export_to_folders(documents)

        logger.info("Generating summary...")
        summary = self.sorter.generate_summary(documents)
        self.exporter.export_summary(summary)

        logger.info("Exporting results...")
        if export_formats:
            export_all(documents, self.output_dir, export_formats)

        successful = len(
        [d for d in documents if (d.vendor or d.amount is not None) and not d.needs_review]
    )
        failed = len(errors) + len([d for d in documents if d.needs_review])

        return ProcessingResult(
            documents=documents,
            total_processed=len(doc_paths),
            successful=successful,
            failed=failed,
            errors=errors,
        )


def run_pipeline(
    input_dir: str,
    output_dir: str,
    model: str = "llama3.2:3b",
    organize_by: str = "category",
    export_formats: list[str] | None = None,
    ollama_host: str = "http://localhost:11434",
) -> ProcessingResult:
    pipeline = InvoiceSorterPipeline(
        input_dir=Path(input_dir),
        output_dir=Path(output_dir),
        model=model,
        organize_by=organize_by,
        ollama_host=ollama_host,
    )
    return pipeline.run(export_formats)