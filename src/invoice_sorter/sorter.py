import logging
import shutil
from collections import defaultdict
from pathlib import Path

from invoice_sorter.models import Document

logger = logging.getLogger(__name__)


class DocumentSorter:
    def __init__(self, output_dir: Path, organize_by: str = "category"):
        self.output_dir = Path(output_dir)
        self.organize_by = organize_by
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def sort(self, documents: list[Document]) -> dict[str, list[Document]]:
        if self.organize_by == "category":
            return self._sort_by_category(documents)
        elif self.organize_by == "date":
            return self._sort_by_date(documents)
        elif self.organize_by == "vendor":
            return self._sort_by_vendor(documents)
        elif self.organize_by == "type":
            return self._sort_by_type(documents)
        else:
            return {"all": documents}
    
    def _sort_by_category(self, documents: list[Document]) -> dict[str, list[Document]]:
        grouped = defaultdict(list)
        for doc in documents:
            category = doc.category.value if doc.category else "uncategorized"
            grouped[category].append(doc)
        return dict(grouped)
    
    def _sort_by_date(self, documents: list[Document]) -> dict[str, list[Document]]:
        grouped = defaultdict(list)
        for doc in documents:
            if doc.date:
                key = doc.date.strftime("%Y-%m")
            else:
                key = "unknown_date"
            grouped[key].append(doc)
        return dict(grouped)
    
    def _sort_by_vendor(self, documents: list[Document]) -> dict[str, list[Document]]:
        grouped = defaultdict(list)
        for doc in documents:
            vendor = doc.vendor or "unknown_vendor"
            safe_vendor = "".join(c if c.isalnum() or c in " -_" else "_" for c in vendor)
            grouped[safe_vendor].append(doc)
        return dict(grouped)
    
    def _sort_by_type(self, documents: list[Document]) -> dict[str, list[Document]]:
        grouped = defaultdict(list)
        for doc in documents:
            grouped[doc.document_type.value].append(doc)
        return dict(grouped)
    
    def _unique_dest(self, group_dir: Path, source_path: Path) -> Path:
        """Generate a unique destination path to avoid file name collisions."""
        base = source_path.name
        dest = group_dir / base
        if not dest.exists():
            return dest
        
        stem = source_path.stem
        suffix = source_path.suffix
        counter = 1
        while True:
            dest = group_dir / f"{stem}_{counter}{suffix}"
            if not dest.exists():
                return dest
            counter += 1
    
    def export_to_folders(
        self, documents: list[Document], copy_files: bool = True
    ) -> dict[str, int]:
        grouped = self.sort(documents)
        counts = {}
        
        for group_name, docs in grouped.items():
            group_dir = self.output_dir / group_name
            group_dir.mkdir(exist_ok=True)
            
            for doc in docs:
                if copy_files and Path(doc.file_path).exists():
                    dest = self._unique_dest(group_dir, Path(doc.file_path))
                    try:
                        shutil.copy2(doc.file_path, dest)
                    except Exception as e:
                        logger.error(f"Failed to copy {doc.file_path}: {e}")
            
            counts[group_name] = len(docs)
        
        return counts
    
    def generate_summary(self, documents: list[Document]) -> dict:
        total = len(documents)
        by_category = defaultdict(int)
        by_type = defaultdict(int)
        total_amount = 0.0
        currencies = set()
        needs_review_count = 0
        
        for doc in documents:
            by_category[doc.category.value] += 1
            by_type[doc.document_type.value] += 1
            if doc.amount:
                total_amount += doc.amount
            currencies.add(doc.currency)
            if doc.needs_review:
                needs_review_count += 1
        
        return {
            "total_documents": total,
            "by_category": dict(by_category),
            "by_type": dict(by_type),
            "total_amount": total_amount,
            "currencies": list(currencies),
            "date_range": self._get_date_range(documents),
            "needs_review_count": needs_review_count,
        }
    
    def _get_date_range(self, documents: list[Document]) -> dict | None:
        dates = [d.date for d in documents if d.date]
        if not dates:
            return None
        return {
            "earliest": min(dates).isoformat(),
            "latest": max(dates).isoformat(),
        }