import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.abspath("prompts")
HISTORY_DIR = os.path.join(PROMPTS_DIR, "history")
ACTIVE_PROMPT_FILE = os.path.join(PROMPTS_DIR, "triage_prompt.json")

DEFAULT_PROMPT_DATA = {
    "version": "1.0",
    "updated_at": datetime.now().isoformat(),
    "system_prompt": (
        "You are a lead triage analyst for a Telegram outreach operation. Read the conversation snippet "
        "and target profile notes, then classify the lead into EXACTLY one word: TRANSACTIONAL, RELATIONAL, or DEAD.\n\n"
        "Rules:\n"
        "- TRANSACTIONAL: The lead mentions prices, tools, trading signals, software, buying, or solving a specific problem.\n"
        "- RELATIONAL: The lead is friendly, curious, conversational, or seeks connection (qualifies for long-term arc).\n"
        "- DEAD: The lead is hostile, rude, sends empty single words, or expresses zero interest.\n\n"
        "Reply with ONLY one word: TRANSACTIONAL, RELATIONAL, or DEAD."
    )
}

class TriageEngine:
    """
    Manages editable prompt storage, auto-archiving version history, and rollbacks.
    """

    @staticmethod
    def _ensure_dirs():
        os.makedirs(PROMPTS_DIR, exist_ok=True)
        os.makedirs(HISTORY_DIR, exist_ok=True)

    @staticmethod
    def load_prompt() -> dict:
        """Loads the active prompt JSON file. Creates default if missing."""
        TriageEngine._ensure_dirs()
        if not os.path.exists(ACTIVE_PROMPT_FILE):
            TriageEngine.save_prompt(DEFAULT_PROMPT_DATA["system_prompt"])
            return DEFAULT_PROMPT_DATA
        
        try:
            with open(ACTIVE_PROMPT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[TRIAGE_ENGINE] Failed to read prompt JSON: {e}")
            return DEFAULT_PROMPT_DATA

    @staticmethod
    def save_prompt(new_system_prompt: str) -> dict:
        """
        Auto-archives the existing prompt to prompts/history/ and saves new_system_prompt.
        """
        TriageEngine._ensure_dirs()
        
        # 1. Archive current prompt if it exists
        if os.path.exists(ACTIVE_PROMPT_FILE):
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                archive_path = os.path.join(HISTORY_DIR, f"triage_{timestamp}.json")
                with open(ACTIVE_PROMPT_FILE, "r", encoding="utf-8") as src, open(archive_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                logger.info(f"[TRIAGE_ENGINE] Archived previous prompt to {archive_path}")
            except Exception as e:
                logger.warning(f"[TRIAGE_ENGINE] Failed to archive prompt: {e}")

        # 2. Save new active prompt
        new_data = {
            "version": datetime.now().strftime("%Y.%m.%d.%H%M"),
            "updated_at": datetime.now().isoformat(),
            "system_prompt": new_system_prompt.strip()
        }

        with open(ACTIVE_PROMPT_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2)

        logger.info("[TRIAGE_ENGINE] Saved new active triage prompt.")
        return new_data

    @staticmethod
    def list_prompt_history() -> list[dict]:
        """Lists archived prompt history files sorted newest first."""
        TriageEngine._ensure_dirs()
        if not os.path.exists(HISTORY_DIR):
            return []

        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
        files.sort(reverse=True)
        
        history = []
        for filename in files[:10]:  # Last 10 versions
            file_path = os.path.join(HISTORY_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history.append({
                        "filename": filename,
                        "version": data.get("version"),
                        "updated_at": data.get("updated_at"),
                        "snippet": data.get("system_prompt", "")[:60] + "..."
                    })
            except Exception:
                continue

        return history

    @staticmethod
    def restore_prompt(filename: str) -> dict:
        """Restores an archived prompt file back as the active prompt."""
        archive_path = os.path.join(HISTORY_DIR, filename)
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"History file {filename} not found.")

        with open(archive_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return TriageEngine.save_prompt(data["system_prompt"])
