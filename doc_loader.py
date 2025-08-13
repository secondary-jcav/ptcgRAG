from __future__ import annotations
"""
doc_loader.py
-------------
Load JSONL files (emitted by CardDocumentBuilder) into LlamaIndex Documents.
Each line must be: {"doc_id": "...", "text": "...", "metadata": {...}}
"""
from pathlib import Path
from typing import Iterable, List, Union
import json
from llama_index.core import Document

def load_jsonl_file(path: Union[str, Path]) -> List[Document]:
    path = Path(path)
    docs: List[Document] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            text = obj.get("text", "")
            metadata = obj.get("metadata", {}) or {}
            docs.append(Document(text=text, metadata=metadata))
    return docs

def load_jsonl_glob(glob_pattern: str) -> List[Document]:
    from glob import glob
    docs: List[Document] = []
    for p in glob(glob_pattern):
        docs.extend(load_jsonl_file(p))
    return docs

def load_storage_dir(storage_dir: Union[str, Path]) -> List[Document]:
    """
    Load all *.jsonl inside a storage dir.
    Example: storage_dir="./storage" (created by CardDocumentBuilder.save_*)
    """
    storage_dir = Path(storage_dir)
    docs: List[Document] = []
    for p in sorted(storage_dir.glob("*.jsonl")):
        docs.extend(load_jsonl_file(p))
    return docs
