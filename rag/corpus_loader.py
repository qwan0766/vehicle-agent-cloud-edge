from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rag.documents import RetrievalDocument


DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def load_markdown_corpus(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> List[RetrievalDocument]:
    if not corpus_dir.exists():
        return []

    documents = []
    for path in sorted(corpus_dir.glob("*.md")):
        parsed = _parse_markdown_document(path)
        if parsed:
            documents.append(parsed)
    return documents


def _parse_markdown_document(path: Path) -> Optional[RetrievalDocument]:
    raw_text = path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return None

    metadata, body = _split_front_matter(raw_text)
    doc_id = metadata.get("doc_id") or path.stem
    keywords = _parse_keywords(metadata.get("keywords", ""))
    topic = metadata.get("topic") or "vehicle_document"

    return RetrievalDocument(
        doc_id=doc_id,
        text=body.strip(),
        keywords=keywords,
        metadata={
            "topic": topic,
            "knowledge_type": "document_rag",
            "source_path": str(path),
            "source_type": "markdown_corpus",
        },
    )


def _split_front_matter(raw_text: str) -> Tuple[Dict[str, str], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text

    lines = raw_text.splitlines()
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, raw_text

    metadata = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    body = "\n".join(lines[end_index + 1 :])
    return metadata, body


def _parse_keywords(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
