from __future__ import annotations
import os
"""
llm_config.py
-------------
Minimal helpers to pin LlamaIndex models in one place.
Call `configure_llm()` at process start (optional).
"""
from typing import Optional
from llama_index.core import Settings

def configure_llm(
    llm_model: Optional[str] = None,
    embed_model: Optional[str] = None,
):
    """
    Set global LlamaIndex models. If None, keep your existing Settings as-is.
    Typical OpenAI defaults:
      llm_model="gpt-4o-mini"
      embed_model="text-embedding-3-small"
    """
    if llm_model:
        from llama_index.llms.openai import OpenAI
        Settings.llm = OpenAI(model=llm_model, api_key=os.getenv("OPENAI_API_KEY"))
    if embed_model:
        from llama_index.embeddings.openai import OpenAIEmbedding
        Settings.embed_model = OpenAIEmbedding(model=embed_model,api_key=os.getenv("OPENAI_API_KEY"))
