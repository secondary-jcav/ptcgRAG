from typing import List

# -----------------------------
# Synergy tag extraction rules
# -----------------------------

TAG_RULES: List[tuple[str, str]] = [
    (r"\b(search|look up|reveal)\s+(your\s+)?(deck|discard)\b", "tutor"),
    (r"\bdraw\b|\bdraw\s+\d+\s+cards?\b", "draw"),
    (r"\battach\s+(an?\s+)?energy\b|\bextra\s+energy\b|\bmore\s+energy\b|\baccelerat(?:e|ion)\b", "energy_accel"),
    (r"\b(heal|remove)\s+(damage|damage\s+counters?)\b", "heal"),
    (r"\b(switch|swap)\s+(your\s+)?(active|benched)\b", "switch"),
    (r"\b(retreat\s+cost|reduce\s+retreat)\b", "retreat_reduction"),
    (r"\bdiscard\s+(a|an|any|up\s+to|from)\b", "discard"),
    (r"\b(search|attach)\s+(a\s+)?tool\b|\bpokemon\s+tool\b", "tool_synergy"),
    (r"\b(evolve|evolution)\b", "evolution"),
    (r"\bresist(s|ance)?\b|\bweakness\b", "type_matchup"),
]

TYPE_WORDS = {
    "Grass": ["grass", "leaf", "plants"],
    "Fire": ["fire", "flame", "burn"],
    "Water": ["water", "aqua", "rain"],
    "Lightning": ["lightning", "electric", "spark"],
    "Psychic": ["psychic", "mind", "psi"],
    "Fighting": ["fighting", "punch", "kick"],
    "Darkness": ["dark", "shadow"],
    "Metal": ["metal", "steel"],
    "Fairy": ["fairy"],
    "Dragon": ["dragon"],
    "Colorless": ["colorless", "neutral"],
}