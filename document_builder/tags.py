from typing import List

# -----------------------------
# Synergy tag extraction rules
# -----------------------------

TAG_RULES: List[tuple[str, str]] = [
    (r"\b(search|look up|reveal) (your )?(deck|discard)", "tutor"),
    (r"\bdraw\b|\bdraw [0-9]+ cards?", "draw"),
    (r"\battach (an? )?energy|extra energy|more energy|accelerat(e|ion)\b", "energy_accel"),
    (r"\b(heal|remove) (damage|damage counters?)\b", "heal"),
    (r"\b(switch|swap) (your )?(active|benched)\b", "switch"),
    (r"\b(retreat cost|reduce retreat)\b", "retreat_reduction"),
    (r"\bdiscard (a|an|any|up to|from)\b", "discard"),
    (r"\b(search|attach) (a )?tool\b|pokemon tool", "tool_synergy"),
    (r"\b(evolve|evolution)\b", "evolution"),
    (r"\bresist(s|ance)?|weakness\b", "type_matchup"),
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