"""Invoice Sorter - Local AI-powered invoice and receipt organizer for freelancers."""

__version__ = "0.1.0"
__author__ = "Priyansh"
__license__ = "MIT"

from invoice_sorter.models import Document, DocumentType, ExpenseCategory, ProcessingResult
from invoice_sorter.pipeline import run_pipeline

__all__ = [
    "Document",
    "DocumentType",
    "ExpenseCategory",
    "ProcessingResult",
    "run_pipeline",
]