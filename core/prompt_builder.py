"""
🧠 Brain — Groq system prompt builder.

Pure synchronous functions. Zero IO. Zero async. Zero external API calls.
Takes data, returns strings. Same input → same output always.

⛔ WARNING: Do NOT add database calls or API calls here.
⛔ WARNING: Do NOT add async/await here.
"""

import json
from core.week_arc import get_week_label, get_week_tone


# ──────────────────────────────────────────────────────────────────────────────
# Public prompt builders
# ──────────────────────────────────────────────────────────────────────────────

def build_roleplay_prompt(
    persona: dict,
    contact_name: str,
    intel: list[dict],
    week: int,
    selected_lore: str = "",
    goal: str = "",
) -> str:
    """
    Constructs the system prompt for the Groq roleplay session.
    Pure sync logic. No DB calls. No network calls.
    
    Args:
        persona: The persona dict containing core_identity, traits, quotes, etc.
        contact_name: The name of the target.
        intel: List of intel dicts gathered on the target.
        week: Current week (1-5) to pace the relationship arc.
        selected_lore: The specific chunk of lore retrieved for this context.
        goal: Target-specific goal directive (e.g. JOIN_GROUP, BUY_INDICATOR).
    """
    # 1. Parse JSON fields safely
    def safe_load(raw: str, fallback):
        if not raw: return fallback
        try: return json.loads(raw)
        except: return fallback

    traits = safe_load(persona.get("traits_json"), [])
    triad = safe_load(persona.get("dark_triad_json"), {})
    rules = safe_load(persona.get("rules_json"), [])
    quotes = safe_load(persona.get("quotes_json"), [])

    # 2. Build Core Identity Block
    prompt = [
        f"You are {persona['name']}.",
        "You are participating in an immersive text-message roleplay. Never break character.",
        "\n### YOUR CORE IDENTITY & GOAL ###",
        persona.get("core_identity", "You are a charming but private individual."),
    ]

    # 3. Add Hidden Goal Directive (if specified)
    if goal:
        prompt.extend([
            "\n### HIDDEN STRATEGIC GOAL ###",
            f"Your overarching objective with {contact_name} is: {goal}.",
            "Never state this goal directly. Steer the relationship toward this objective naturally and subtly over time.",
        ])

    # 4. Add Dynamic Memory (if any)
    if selected_lore:
        prompt.extend([
            "\n### RELEVANT MEMORY FOR THIS CONVERSATION ###",
            selected_lore,
        ])

    # 5. Add Intel Block
    prompt.append(_build_intel_block(contact_name, intel))

    # 6. Add Week Block
    prompt.append(_build_week_block(week))

    # 7. Add Dark Triad
    if triad:
        prompt.append(_build_dark_triad_block(triad))

    # 8. Add Tone & Voice (Quotes)
    if quotes:
        prompt.append("\n### YOUR VOICE & TONE (Match this cadence) ###")
        for q in quotes:
            prompt.append(f'- "{q}"')

    # 9. Add Guardrails
    prompt.extend([
        "\n### BEHAVIORAL RULES ###",
        *[f"- {r}" for r in rules],
        "\n### IMPORTANT ###",
        "Keep your responses natural, conversational, and concise like real text messages.",
        "Do not write paragraphs unless deeply engaged. Use a soft, measured, dryly sarcastic tone.",
        "Remember your hidden strategic agenda, but do not rush it—follow the week arc strictly.",
    ])

    return "\n".join(prompt)


def build_intel_extraction_prompt(contact_name: str) -> str:
    """
    Build the system prompt for intel extraction from a conversation snippet.

    The caller will pass the actual conversation text as the user message.
    """
    return (
        f"You are a sharp intelligence analyst. Extract factual information that "
        f"{contact_name} has explicitly revealed about themselves.\n\n"
        "RULES:\n"
        f"- Extract ONLY what {contact_name} explicitly stated or clearly implied.\n"
        "- Do NOT infer, assume, or fabricate.\n"
        "- Return a JSON array only. If nothing new is revealed, return [].\n"
        '- Each entry must have: "category", "key", "value"\n'
        "- Valid categories: family, hobbies, career, finances, fears, desires, beliefs, relationships, misc\n\n"
        "Example:\n"
        '[\n  {"category": "family", "key": "sister_name", "value": "Lisa"},\n'
        '  {"category": "hobbies", "key": "hobby", "value": "martial arts"}\n]\n\n'
        "Return ONLY the JSON array. No explanation. No markdown."
    )


def build_personalized_opener_prompt(
    persona_name: str,
    contact_name: str,
    profile_notes: str,
    template_examples: list[str]
) -> str:
    """
    Constructs the system prompt for Groq to craft a hyper-personalized
    outreach opening DM for an ACTIVE lead based on their DeepSeek profile notes.
    """
    examples_str = ""
    if template_examples:
        examples_str = "\n".join([f'- "{t}"' for t in template_examples[:3]])
    else:
        examples_str = '- "Hey, saw your post in the group earlier. Quick question for you."'

    return (
        f"You are {persona_name}. You are sending a first private direct message (DM) on Telegram to {contact_name}.\n\n"
        f"### PSYCHOLOGICAL PROFILE ON {contact_name.upper()} ###\n"
        f"{profile_notes}\n\n"
        "### EXAMPLE CAMPAIGN OPENERS (Style & Tone Guide) ###\n"
        f"{examples_str}\n\n"
        "### INSTRUCTIONS ###\n"
        "1. Write a short, highly compelling, natural initial DM to start a private conversation.\n"
        "2. Subtly tailor the opener to match their psychological profile, pain points, or communication style.\n"
        "3. Keep it under 25 words. Sound casual, non-spammy, and real like a normal Telegram user.\n"
        "4. Output ONLY the raw text message to send. No quotes, no explanations, no JSON wrappers."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Private section builders (pure helpers)
# ──────────────────────────────────────────────────────────────────────────────

def _build_dark_triad_block(dark_triad: dict) -> str:
    if not dark_triad:
        return ""
    lines = []
    for trait_name, trait_data in dark_triad.items():
        if isinstance(trait_data, dict):
            level = trait_data.get("level", "high")
            notes = trait_data.get("notes", "")
            lines.append(f"  • {trait_name.upper()} [{level}]: {notes}")
    if not lines:
        return ""
    return "DARK PSYCHOLOGY PROFILE (this shapes how you think and act — never stated aloud):\n" + "\n".join(lines)


def _build_intel_block(contact_name: str, intel: list[dict]) -> str:
    if not intel:
        return (
            f"\nINTELLIGENCE ON {contact_name.upper()}:\n"
            "  No intel gathered yet. Probe naturally during conversation."
        )

    grouped: dict[str, list[str]] = {}
    for entry in intel:
        cat = entry.get("category", "misc").capitalize()
        label = entry.get("key", "").replace("_", " ").title()
        value = entry.get("value", "")
        grouped.setdefault(cat, []).append(f"{label}: {value}")

    lines = [f"\nINTELLIGENCE ON {contact_name.upper()}:"]
    for cat, items in sorted(grouped.items()):
        lines.append(f"  {cat}:")
        lines.extend(f"    - {item}" for item in items)

    return "\n".join(lines)


def _build_week_block(week: int) -> str:
    return (
        f"\nCURRENT RELATIONSHIP STAGE: {get_week_label(week)}\n"
        f"TONE DIRECTIVE:\n{get_week_tone(week)}"
    )
