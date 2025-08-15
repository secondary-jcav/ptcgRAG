from __future__ import annotations
"""
CardDocumentBuilder
-------------------
Build one document per card (plus guides) with optional synergy tags, then save
as JSONL into a /storage directory. Documents are stored as plain JSON objects
with fields: {"doc_id", "text", "metadata"}. You can later load them and
convert to LlamaIndex `Document`s for indexing.

Usage (CLI):
  python card_document_builder.py ./A3b.json ./rules.txt ./deckbuilding.txt \
      --out all_docs.jsonl --per-expansion

This writes:
  ./storage/all_docs.jsonl
  ./storage/cards_A3b.jsonl (if --per-expansion)
"""
import argparse
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from document_builder.tags import TAG_RULES, TYPE_WORDS


# helpers for evolution + normalization
_STAGE_TIER = {
    "basic": 0, "stage 1": 1, "stage1": 1, "stage-1": 1,
    "stage 2": 2, "stage2": 2, "stage-2": 2,
}

def _norm_name(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def _slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _join_list(values: Any) -> str:
    return " | ".join(map(str, values)) if isinstance(values, list) else str(values)


def extract_synergy_tags(text: str, types: Optional[List[str]] = None) -> List[str]:
    text_l = text.lower()
    tags = set()
    for pattern, tag in TAG_RULES:
        if re.search(pattern, text_l):
            tags.add(tag)
    if types:
        for t in types:
            tags.add(f"type:{t}")
            for alias in TYPE_WORDS.get(t, []):
                if alias in text_l:
                    tags.add(f"type_kw:{t}")
    return sorted(tags)


@dataclass
class StoredDoc:
    doc_id: str
    text: str
    metadata: Dict[str, Any]

    def to_json(self) -> Dict[str, Any]:
        return {"doc_id": self.doc_id, "text": self.text, "metadata": self.metadata}


class CardDocumentBuilder:
    def __init__(self, storage_dir: str = "./storage", compute_synergy_tags: bool = True) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.compute_synergy_tags = compute_synergy_tags

    # -------------------------------
    # Public: build + save entrypoint
    # -------------------------------
    def build_from_paths(self, inputs: Iterable[str | Path]) -> List[StoredDoc]:
        docs: List[StoredDoc] = []
        for p in map(Path, inputs):
            if p.suffix.lower() == ".json":
                data = json.loads(p.read_text(encoding="utf-8"))
                docs.extend(self._expansion_to_docs(data, expansion_name=p.stem))
            else:
                # Treat as ancillary text (rules, deckbuilding)
                txt = p.read_text(encoding="utf-8")
                sd = self._text_to_doc(txt, name=p.stem)
                docs.append(sd)
        return docs

    def save_jsonl(self, docs: List[StoredDoc], filename: str = "all_docs.jsonl") -> Path:
        out = self.storage_dir / filename
        with out.open("w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d.to_json(), ensure_ascii=False) + "\n")
        return out

    def save_per_expansion(self, docs: List[StoredDoc]) -> List[Path]:
        groups: Dict[str, List[StoredDoc]] = {}
        for d in docs:
            exp = d.metadata.get("expansion", "misc")
            groups.setdefault(exp, []).append(d)
        written: List[Path] = []
        for exp, group in groups.items():
            fn = self.storage_dir / f"cards_{exp}.jsonl"
            with fn.open("w", encoding="utf-8") as f:
                for d in group:
                    f.write(json.dumps(d.to_json(), ensure_ascii=False) + "\n")
            written.append(fn)
        return written

    # --------------------
    # Internal builders
    # --------------------
    def _text_to_doc(self, text: str, *, name: str) -> StoredDoc:
        meta = {
            "doc_type": "guide",
            "name": name,
        }
        return StoredDoc(doc_id=str(uuid.uuid4()), text=text, metadata=meta)

    def _pokemon_to_doc(self, card: Dict[str, Any], expansion: str) -> StoredDoc:
        name = _norm_name(card.get("name") or "UNKNOWN")
        types = card.get("types") or []
        stage = _norm_name(card.get("stage"))
        evolves_from = _norm_name(card.get("evolves_from"))
        stage_tier = _STAGE_TIER.get(stage.lower(), None)

        lines: List[str] = [
            f"card: {name}",
            "type: pokemon",
            f"expansion: {expansion}",
        ]
        for k in ("stage", "hp", "retreat", "evolves_from", "weakness"):
            if card.get(k) not in (None, "", []):
                lines.append(f"{k}: {_join_list(card[k])}")
        if types:
            lines.append(f"types: {_join_list(types)}")

        abilities_text = []
        for ab in card.get("abilities") or []:
            if isinstance(ab, dict):
                for ab_name, ab_text in ab.items():
                    lines.append(f"ability.{ab_name}: {ab_text}")
                    abilities_text.append(str(ab_text))
            else:
                lines.append(f"ability: {ab}")
                abilities_text.append(str(ab))

        attacks_text = []
        for atk in card.get("attacks") or []:
            a_name = (atk.get("name") or "attack").strip()
            if atk.get("cost"):
                lines.append(f"attack.{a_name}.cost: {_join_list(atk['cost'])}")
            if "damage" in atk and atk["damage"] not in (None, ""):
                lines.append(f"attack.{a_name}.damage: {atk['damage']}")
            if atk.get("effect"):
                lines.append(f"attack.{a_name}.effect: {atk['effect']}")
                attacks_text.append(str(atk["effect"]))

        text = "\n".join(lines)
        tags = extract_synergy_tags("\n".join(abilities_text + attacks_text),
                                    types) if self.compute_synergy_tags else []

        # >>> NEW evolution-aware metadata
        evolution_base = card.get("_evolution_base") or name
        has_children = bool(card.get("_has_children"))
        meta = {
            "doc_type": "card",
            "card_type": "pokemon",
            "name": name,
            "name_slug": _slug(name),
            "expansion": expansion,
            "types": types,
            "stage": stage,
            "stage_tier": stage_tier,
            "evolves_from": evolves_from,  # <-- add this
            "evolves_from_slug": _slug(evolves_from) if evolves_from else "",
            "evolution_base": evolution_base,  # <-- base of the chain
            "evolution_base_slug": _slug(evolution_base),
            "has_evolutions": has_children,  # <-- parent has children
            "synergy_tags": tags,
        }
        return StoredDoc(doc_id=str(uuid.uuid4()), text=text, metadata=meta)

    def _named_effect_to_doc(self, card: Dict[str, Any], expansion: str, section: str) -> StoredDoc:
        name = (card.get("name") or "UNKNOWN").strip()
        effect = card.get("effect") or ""
        lines = [
            f"card: {name}",
            f"type: {section}",
            f"expansion: {expansion}",
        ]
        if effect:
            lines.append(f"effect: {effect}")
        text = "\n".join(lines)
        tags = extract_synergy_tags(effect) if self.compute_synergy_tags else []
        meta = {
            "doc_type": "card",
            "card_type": section,
            "name": name,
            "expansion": expansion,
            "synergy_tags": tags,
        }
        return StoredDoc(doc_id=str(uuid.uuid4()), text=text, metadata=meta)

    def _expansion_to_docs(self, expansion_json: Dict[str, Any], expansion_name: str) -> List[StoredDoc]:
        docs: List[StoredDoc] = []
        pokemon_list = expansion_json.get("pokemon") or []

        # Map: normalized card name -> raw card dict
        name_map = {_norm_name(p.get("name")): p for p in pokemon_list if p.get("name")}

        # Compute base for each pokemon by walking evolves_from up the chain
        def _find_base(n: str) -> str:
            seen = set()
            cur = n
            while cur and cur not in seen:
                seen.add(cur)
                card = name_map.get(cur)
                if not card:
                    break
                parent = _norm_name(card.get("evolves_from"))
                if not parent:
                    return cur
                cur = parent
            return n  # fallback

        # Which mons have children?
        has_children: set[str] = set()
        for p in pokemon_list:
            parent = _norm_name(p.get("evolves_from"))
            if parent:
                has_children.add(parent)

        # Build docs with enriched metadata
        for p in pokemon_list:
            nm = _norm_name(p.get("name"))
            base = _find_base(nm)
            # pass hints to _pokemon_to_doc via extra fields on the card
            p = dict(p)  # shallow copy
            p["_norm_name"] = nm
            p["_evolution_base"] = base
            p["_has_children"] = (nm in has_children)
            docs.append(self._pokemon_to_doc(p, expansion_name))

        # supporters/items/tools
        for sec in ("supporters", "items", "tools"):
            for c in (expansion_json.get(sec) or []):
                docs.append(self._named_effect_to_doc(c, expansion_name, sec))

        return docs

    # --------------------
    # Optional: load later
    # --------------------
    @staticmethod
    def load_jsonl(path: str | Path) -> List[StoredDoc]:
        path = Path(path)
        out: List[StoredDoc] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    out.append(StoredDoc(doc_id=obj.get("doc_id", str(uuid.uuid4())),
                                         text=obj["text"], metadata=obj.get("metadata", {})))
        return out

    @staticmethod
    def to_llama_documents(docs: List[StoredDoc]):
        """Convert to LlamaIndex Documents if the library is available."""
        try:
            from llama_index.core import Document as LIDocument
        except Exception as e:  # pragma: no cover - optional dep
            raise RuntimeError("llama_index is not installed. pip install llama-index") from e
        return [LIDocument(text=d.text, metadata=d.metadata) for d in docs]


# ----------------
# CLI Entrypoint
# ----------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build per-card documents and save to /storage")
    ap.add_argument("inputs", nargs="+", help="Paths to JSON expansions and/or TXT guides")
    ap.add_argument("--out", default="all_docs.jsonl", help="Filename for combined JSONL (in /storage)")
    ap.add_argument("--no-synergy-tags", action="store_true", help="Disable synergy tag extraction")
    ap.add_argument("--per-expansion", action="store_true", help="Also write one JSONL per expansion")
    ap.add_argument("--storage", default="./storage", help="Storage directory (default: ./storage)")
    args = ap.parse_args()

    builder = CardDocumentBuilder(storage_dir=args.storage, compute_synergy_tags=not args.no_synergy_tags)
    built = builder.build_from_paths(args.inputs)
    combined_path = builder.save_jsonl(built, filename=args.out)
    print(f"Wrote combined: {combined_path}")
    if args.per_expansion:
        for p in builder.save_per_expansion(built):
            print(f"Wrote: {p}")
