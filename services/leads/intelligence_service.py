import json
import logging
import uuid
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from data.repositories.target_repo import get_target_by_id, update_target_relational_data
from data.repositories.mirror_observations_repo import MirrorObservationsRepository
from providers.groq_client import groq_client

logger = logging.getLogger(__name__)

# Stop-list for TRIVIAL messages (blank, single emoji/punctuation, trivial noise)
TRIVIAL_REGEX = re.compile(r"^[\s\W\d]*$", re.UNICODE)

MIRROR_SYSTEM_PROMPT = """You are an expert NLP style analyst.
Your task is to analyze a set of Python-extracted messaging statistics and recent sample messages from a chat target to extract their Communication Style Profile.

Return ONLY a raw, valid JSON object with the following schema and no markdown formatting:
{
  "formality": "casual" | "neutral" | "formal",
  "verbosity": "short" | "medium" | "long",
  "emoji_usage": "none" | "low" | "high",
  "slang_usage": "none" | "low" | "high",
  "punctuation": "minimal" | "standard" | "heavy",
  "caps_usage": "lowercase" | "standard" | "ALL_CAPS",
  "tone": "enthusiastic" | "neutral" | "cynical" | "curious" | "direct",
  "confidence_score": integer (0 to 100)
}
"""

class IntelligenceService:
    """
    Intelligence & Mirroring Engine (Phase 7).
    Analyzes target communication style using Python local statistics + Groq LLM interpretation.
    Optimized to minimize LLM token calls using triviality filtering, diversity triggers,
    high-information overrides, and local style-drift detection.
    """

    @staticmethod
    def is_trivial_message(message_text: str) -> bool:
        """
        Returns True if the message is zero-value trivial noise (empty, whitespace, or single punctuation/emoji).
        Short tone words ("wow", "damn", "seriously?") are NOT trivial.
        """
        if not message_text or not message_text.strip():
            return True
        text = message_text.strip()
        # Single symbol/punctuation
        if len(text) == 1 and not text.isalnum():
            return True
        return False

    @staticmethod
    def extract_local_features(messages: List[str]) -> Dict[str, Any]:
        """
        Microsecond Python feature extraction across a set of messages.
        Python measures, Groq interprets.
        """
        if not messages:
            return {
                "avg_word_count": 0,
                "emoji_count": 0,
                "caps_ratio": 0.0,
                "question_ratio": 0.0
            }

        total_words = 0
        total_chars = 0
        upper_chars = 0
        question_count = 0
        emoji_count = 0

        # Simple emoji pattern matching
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)

        for msg in messages:
            words = msg.split()
            total_words += len(words)
            total_chars += len(msg)
            upper_chars += sum(1 for c in msg if c.isupper())
            if "?" in msg:
                question_count += 1
            emoji_count += len(emoji_pattern.findall(msg))

        avg_words = total_words / len(messages)
        caps_ratio = (upper_chars / total_chars) if total_chars > 0 else 0.0
        question_ratio = question_count / len(messages)

        return {
            "avg_word_count": round(avg_words, 2),
            "emoji_count": emoji_count,
            "caps_ratio": round(caps_ratio, 2),
            "question_ratio": round(question_ratio, 2)
        }

    @staticmethod
    def calculate_stylistic_diversity(messages: List[str]) -> float:
        """
        Calculates lexical diversity (unique words / total words) across buffered messages.
        """
        all_words = []
        for msg in messages:
            all_words.extend([w.lower().strip(".,!?") for w in msg.split() if w])
        if not all_words:
            return 0.0
        return len(set(all_words)) / len(all_words)

    @staticmethod
    def detect_style_drift(stored_profile: Optional[Dict[str, Any]], new_message: str) -> bool:
        """
        Cheap local style-drift detector.
        Checks if a target mapped as casual/short suddenly sends formal/structured messages,
        or vice versa.
        """
        if not stored_profile:
            return False

        words = new_message.split()
        word_count = len(words)
        has_formal_markers = any(m in new_message.lower() for m in ["good afternoon", "good morning", "regards", "sincerely", "discuss the proposal", "furthermore"])
        is_first_letter_capitalized = new_message[0].isupper() if new_message else False
        has_ending_period = new_message.endswith(".")

        stored_formality = stored_profile.get("formality", "casual")

        if stored_formality == "casual":
            if has_formal_markers or (word_count > 12 and is_first_letter_capitalized and has_ending_period):
                logger.info(f"[INTELLIGENCE_SERVICE] Style Drift Detected: Casual target sent formal message '{new_message[:30]}...'")
                return True

        if stored_formality == "formal":
            if any(s in new_message.lower() for s in ["lol", "nah", "fr", "tbh", "bruh", "lmao"]):
                logger.info(f"[INTELLIGENCE_SERVICE] Style Drift Detected: Formal target sent casual slang '{new_message[:30]}...'")
                return True

        return False

    async def process_inbound_message(
        self,
        session: AsyncSession,
        target_id: int,
        message_text: str,
        relationship_message_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Main entrypoint called when an inbound message arrives.
        Decoupled interface working around target_id and message strings.
        Returns the active mirror profile dict.
        """
        if self.is_trivial_message(message_text):
            logger.info(f"[INTELLIGENCE_SERVICE] Skipping trivial message for target_id={target_id}")
            target = await get_target_by_id(session, target_id)
            if target and target.mirror_profile_json:
                try:
                    return json.loads(target.mirror_profile_json)
                except Exception:
                    pass
            return None

        # 1. Persist observation into database buffer
        repo = MirrorObservationsRepository(session)
        await repo.add_observation(target_id, message_text, relationship_message_id)

        target = await get_target_by_id(session, target_id)
        if not target:
            return None

        stored_profile = None
        if target.mirror_profile_json:
            try:
                stored_profile = json.loads(target.mirror_profile_json)
            except Exception:
                stored_profile = None

        current_confidence = target.mirror_confidence or 0
        pending_obs = await repo.get_pending_observations(target_id)
        pending_texts = [obs.message_text for obs in pending_obs]

        # 2. Evaluate Triggers
        words_list = [w for w in message_text.split() if w]
        is_high_info = len(words_list) >= 40
        is_drift = self.detect_style_drift(stored_profile, message_text)
        diversity_score = self.calculate_stylistic_diversity(pending_texts)
        is_batch_ready = len(pending_texts) >= 5 or (len(pending_texts) >= 3 and diversity_score > 0.7)

        should_trigger = False

        if is_high_info:
            logger.info(f"[INTELLIGENCE_SERVICE] High-Information Override (>50 words) triggered for target_id={target_id}")
            should_trigger = True
        elif is_drift:
            logger.info(f"[INTELLIGENCE_SERVICE] Style Drift Triggered for target_id={target_id}")
            should_trigger = True
        elif current_confidence < 85 and is_batch_ready:
            logger.info(f"[INTELLIGENCE_SERVICE] Routine Batch Triggered (Count={len(pending_texts)}, Div={round(diversity_score, 2)}) for target_id={target_id}")
            should_trigger = True

        if not should_trigger:
            return stored_profile

        # 3. Atomic Batch Claiming
        batch_id = str(uuid.uuid4())
        claimed = await repo.claim_pending_batch(target_id, batch_id)
        if not claimed:
            return stored_profile

        claimed_texts = [c.message_text for c in claimed]

        # 4. Local Python Stats Extraction
        local_stats = self.extract_local_features(claimed_texts)

        # 5. Call Groq for Style Synthesis
        groq_payload = {
            "local_features": local_stats,
            "previous_profile": stored_profile,
            "samples": claimed_texts[-5:]  # Send at most 5 recent samples
        }

        user_prompt = f"Analyze the following user communication features and sample messages:\n{json.dumps(groq_payload, indent=2)}"

        try:
            raw_response = await groq_client.chat_complete(MIRROR_SYSTEM_PROMPT, user_prompt)
            # Clean possible markdown blocks
            clean_res = raw_response.strip()
            if clean_res.startswith("```"):
                clean_res = re.sub(r"^```[a-z]*\n?", "", clean_res, flags=re.IGNORECASE)
                clean_res = re.sub(r"\n?```$", "", clean_res).strip()

            parsed_profile = json.loads(clean_res)
            new_confidence = int(parsed_profile.get("confidence_score", 75))

            # If style drift occurred on a previously high confidence profile, lower confidence appropriately
            if is_drift and current_confidence >= 85:
                new_confidence = min(new_confidence, 75)

            # 6. Save Profile and Mark Batch Analyzed
            await update_target_relational_data(
                session,
                target_id=target_id,
                mirror_profile_json=json.dumps(parsed_profile),
                mirror_confidence=new_confidence
            )
            await repo.mark_batch_analyzed(batch_id)
            logger.info(f"[INTELLIGENCE_SERVICE] Successfully updated mirror profile for target_id={target_id} (Confidence={new_confidence})")
            return parsed_profile

        except Exception as exc:
            logger.warning(f"[INTELLIGENCE_SERVICE] Mirroring analysis failed for target_id={target_id}: {exc}")
            return stored_profile

intelligence_service = IntelligenceService()
