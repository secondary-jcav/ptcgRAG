from __future__ import annotations
"""
synergy_query.py (LlamaIndex 0.13.1 compatible)
----------------------------------------------
Query helpers for "find synergies" using a VectorStoreIndex.
- Uses a real BaseNodePostprocessor subclass (fixes AttributeError).
- Import paths are compatible with >=0.13 (with gentle fallbacks).
"""
import json
from typing import List, Optional, Callable
try:
    from pydantic import PrivateAttr  # works for Pydantic v1 & v2
except Exception:  # pragma: no cover
    PrivateAttr = None


from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer

# Import NodeWithScore + BaseNodePostprocessor with fallbacks
try:
    from llama_index.core.schema import NodeWithScore  # 0.13.x
except Exception:  # pragma: no cover
    from llama_index.core.schema import NodeWithScore  # older fallback (same path in many versions)

try:
    from llama_index.core.postprocessor.types import BaseNodePostprocessor  # 0.13.x
except Exception:  # pragma: no cover
    try:
        from llama_index.core.postprocessor import BaseNodePostprocessor  # older fallback
    except Exception:
        class BaseNodePostprocessor:
            # minimal stub that proxies to _postprocess_nodes if present
            def postprocess_nodes(self, nodes, query_bundle=None):
                fn = getattr(self, "_postprocess_nodes", None)
                if callable(fn):
                    return fn(nodes, query_bundle=query_bundle)
                return nodes


DEFAULT_SYSTEM_PROMPT = (
    "You are a competitive deck builder. Given card snippets and (optionally) rules/guide snippets, "
    "recommend synergistic cards across pokemon, supporters, items, and tools. "
    "Favor energy acceleration, tutoring, draw, switching, and type synergies. "
    "Always explain briefly *why* each pick helps, and cite with 'Card Name (Expansion)'. "
)

# replace your _LambdaPostprocessor with this version
class _LambdaPostprocessor(BaseNodePostprocessor):
    # Pydantic-safe storage for the callable
    if PrivateAttr is not None:
        _fn: Callable[[List[NodeWithScore]], List[NodeWithScore]] = PrivateAttr(default=None)

    def __init__(self, fn: Callable[[List[NodeWithScore]], List[NodeWithScore]]):
        # Important: initialize the BaseModel first so internal state is set up
        try:
            super().__init__()  # BaseNodePostprocessor is a Pydantic BaseModel in 0.13.x
        except TypeError:
            # fallback in case the base isn't a model or requires args in older versions
            try:
                super().__init__(**{})  # no-op, avoids passing unknown fields
            except Exception:
                pass

        # Assign the function in a way that's compatible with Pydantic models
        if PrivateAttr is not None:
            self._fn = fn
        else:
            # Non-Pydantic fallback (e.g., if you're using the stub/older versions)
            self._fn = fn

    # REQUIRED by 0.13.x abstract interface
    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle=None) -> List[NodeWithScore]:
        return self._fn(nodes)

    # Keep for cross-version compatibility
    def postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle=None) -> List[NodeWithScore]:
        return self._fn(nodes)


class SynergyQueryEngine:
    def __init__(
        self,
        index: VectorStoreIndex,
        similarity_top_k: int = 8,
        node_postprocessor: Optional[Callable[[List[NodeWithScore]], List[NodeWithScore]]] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.index = index
        self.similarity_top_k = similarity_top_k
        self.node_postprocessor = node_postprocessor
        self.system_prompt = system_prompt

    def _make_engine(self, k: Optional[int] = None, postproc: Optional[Callable] = None) -> RetrieverQueryEngine:
        retriever = VectorIndexRetriever(index=self.index, similarity_top_k=k or self.similarity_top_k)
        synth = get_response_synthesizer()  # default settings
        node_postprocessors = []
        if postproc is not None:
            node_postprocessors = [_LambdaPostprocessor(postproc)]
        engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=synth,
            node_postprocessors=node_postprocessors,
        )
        return engine

    def _default_post_filter(self, target_name: str, expansion: Optional[str], include_cross_expansions: bool):
        def _filter(nodes: List[NodeWithScore]) -> List[NodeWithScore]:
            out: List[NodeWithScore] = []
            for n in nodes:
                # FIX: NodeWithScore -> node.metadata (not n.metadata)
                md = (getattr(n, "node", None).metadata or {}) if getattr(n, "node", None) else {}
                if md.get("doc_type") not in ("card", "guide"):
                    continue
                # Exclude the target card doc itself
                if md.get("doc_type") == "card":
                    same_name = md.get("name", "").lower() == (target_name or "").lower()
                    same_exp = (expansion is None) or (md.get("expansion") == expansion)
                    if same_name and same_exp:
                        continue
                    if not include_cross_expansions and expansion and md.get("expansion") != expansion:
                        continue
                out.append(n)
            return out
        return _filter

    def find_synergies(
        self,
        target_card_name: str,
        expansion: Optional[str] = None,
        include_cross_expansions: bool = True,
        k: Optional[int] = None,
    ) -> str:
        """
        Return a natural-language answer with recommended synergies.
        """
        # First, try to pull target card info so we can craft a focused query
        info_engine = self._make_engine(k=25)
        info_query = (
            f"Return a compact JSON with keys name, expansion, types, synergy_tags for the card named "
            f"'{target_card_name}'. If multiple expansions exist, prefer '{expansion}' if provided."
        )
        info_result = info_engine.query(info_query)
        types, tags = [], []
        try:
            body = str(info_result)
            if "```json" in body:
                body = body.split("```json")[-1].split("```")[0]
            obj = json.loads(body)
            types = obj.get("types") or []
            tags = obj.get("synergy_tags") or []
        except Exception:
            pass

        tag_text = ", ".join(tags) if tags else ""
        types_text = ", ".join(types) if types else ""

        user_query = (
            f"Suggest cards that synergize with {target_card_name}"
            + (f" (types: {types_text})" if types_text else "")
            + (f" using themes: {tag_text}" if tag_text else "")
            + ". Explain why each pick helps a competitive deck."
        )

        postproc = self.node_postprocessor or self._default_post_filter(
            target_card_name, expansion, include_cross_expansions
        )
        engine = self._make_engine(k=k, postproc=postproc)
        result = engine.query(f"{self.system_prompt}\n\nUSER QUERY: {user_query}")
        return str(result)
