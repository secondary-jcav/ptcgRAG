from __future__ import annotations
"""
rag_index.py
------------
Build and (optionally) persist a VectorStoreIndex from LlamaIndex Documents.
"""
from typing import List, Optional
from pathlib import Path
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Document

def build_index(
    documents: List[Document],
    persist_dir: Optional[str] = None,
) -> VectorStoreIndex:
    """
    Build an in-memory VectorStoreIndex (and optionally persist it).
    """
    index = VectorStoreIndex.from_documents(documents)
    if persist_dir:
        storage_context = index.storage_context
        storage_context.persist(persist_dir=persist_dir)
    return index

def load_persisted_index(persist_dir: str) -> VectorStoreIndex:
    """
    Load a VectorStoreIndex that was previously persisted via build_index(..., persist_dir=...).
    """
    persist_dir = str(Path(persist_dir))
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    return index
