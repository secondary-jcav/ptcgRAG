# main.py
from llm_config import configure_llm
from doc_loader import load_storage_dir
from rag_index import build_index, load_persisted_index
from synergy_query import SynergyQueryEngine

# 1) (Optional) pin your models once
configure_llm(llm_model="gpt-5", embed_model="text-embedding-3-large")

# 2) Load docs produced by CardDocumentBuilder
docs = load_storage_dir("./storage")  # or wherever you wrote your JSONL

# 3) Build the index (persist if you want to reuse later)
# index = build_index(docs, persist_dir="./index_store")

# Or later:
index = load_persisted_index("./index_store")

# 4) Query for synergies
engine = SynergyQueryEngine(index)
print(engine.find_synergies("Leafeon", expansion="A3b"))
