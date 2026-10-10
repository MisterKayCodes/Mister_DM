"""
🧠 Brain — Topic Classifier.

Builds a prompt to classify a user's message into one of the persona's lore branches.
Pure synchronous logic. Returns a prompt string.
"""

def build_classification_prompt(contact_name: str, message: str) -> str:
    """
    Builds a prompt to classify the user's intent.
    We need to know which branch of the persona's memory to activate.
    """
    return f"""You are an intent classifier for a roleplay system.
Analyze the following message from '{contact_name}' and classify the core topic into EXACTLY ONE of the following categories:

Categories:
- social: Mentions friends, family, dating history, exes, or social life.
- career: Mentions work, jobs, money, AI consulting, investments, crypto, or net worth.
- philosophy: Mentions beliefs, institutions, privacy, AI future, conspiracy, or life philosophy.
- routine: Mentions daily habits, waking up, diet, skincare, fitness, or coffee.
- travel: Mentions travel, locations, Austin, Lisbon, or destinations.
- none: Generic greeting, short response, or none of the above.

Message: "{message}"

Reply with EXACTLY ONE WORD from the categories list above. No punctuation, no explanation."""
