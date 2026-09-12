import asyncio
import json
import logging

from data.database import AsyncSessionLocal
from data.repositories import (
    target_repo,
    personas_repo,
    intel_repo,
    relationship_chats_repo,
    relationship_messages_repo,
    intents_repo
)
from core.prompt_builder import build_roleplay_prompt, build_intel_extraction_prompt
from core.topic_classifier import build_classification_prompt
from core.intel_parser import parse_intel_response
from providers.groq_client import groq_client
from clients.simulator_client import simulator_client

logger = logging.getLogger(__name__)


class RelationshipService:
    """
    Orchestrates automated roleplay conversations, intelligence extraction,
    and intent logging for RELATIONAL leads.
    """

    @staticmethod
    async def handle_reply(
        target_id: int,
        inbound_message: str,
        session_name: str = "default_session"
    ) -> dict | None:
        """
        Executes the full 11-step relational response cycle for an inbound target reply.
        """
        async with AsyncSessionLocal() as session:
            # 1. Load target context
            target = await target_repo.get_target_by_id(session, target_id)
            if not target:
                logger.error(f"[RELATIONSHIP_SERVICE] Target ID {target_id} not found.")
                return None

            # Determine persona (Elena ID 1 for RELATIONAL, Marcus ID 2 for TRANSACTIONAL fallback)
            persona_id = getattr(target, "assigned_persona_id", None) or 1
            persona_obj = await personas_repo.get_persona(session, persona_id)
            if not persona_obj:
                # Fallback to first persona in DB if persona_id not found
                all_p = await personas_repo.get_all_personas(session)
                if not all_p:
                    logger.error("[RELATIONSHIP_SERVICE] No personas seeded in database.")
                    return None
                persona_obj = all_p[0]

            persona = {
                "name": persona_obj.name,
                "core_identity": persona_obj.core_identity,
                "lore_branches_json": persona_obj.lore_branches_json,
                "traits_json": persona_obj.traits_json,
                "quotes_json": persona_obj.quotes_json,
                "dark_triad_json": persona_obj.dark_triad_json,
                "rules_json": persona_obj.rules_json,
            }

            # Get or create RelationshipChat
            chat = await relationship_chats_repo.get_or_create_chat(
                session=session,
                target_id=target_id,
                persona_id=persona_obj.id,
                goal=getattr(target, "goal", None)
            )

            # Fetch intel entries
            intel_db = await intel_repo.get_intel_for_target(session, target_id)
            intel_list = [
                {"category": i.category, "key": i.key, "value": i.value}
                for i in intel_db
            ]

            # Fetch history
            recent_msgs = await relationship_messages_repo.get_recent_messages(
                session=session,
                chat_id=chat.id,
                limit=30
            )

            # 2. Topic classification (cheap call / prompt building)
            selected_lore = ""
            try:
                class_prompt = build_classification_prompt(
                    contact_name=target.username or "friend",
                    message=inbound_message
                )
                topic = await groq_client.chat_complete(
                    system_prompt="You are a single-word topic classifier.",
                    user_prompt=class_prompt
                )
                topic_clean = topic.strip().lower()

                # Pick matching lore branch from persona
                if persona.get("lore_branches_json"):
                    lore_dict = json.loads(persona["lore_branches_json"])
                    selected_lore = lore_dict.get(topic_clean, "")
            except Exception as exc:
                logger.warning(f"[RELATIONSHIP_SERVICE] Topic classification skipped ({exc})")

            # Process NLP Mirroring via IntelligenceService
            mirror_profile = None
            try:
                from services.intelligence_service import intelligence_service
                mirror_profile = await intelligence_service.process_inbound_message(
                    session=session,
                    target_id=target_id,
                    message_text=inbound_message
                )
            except Exception as exc:
                logger.warning(f"[RELATIONSHIP_SERVICE] IntelligenceService processing failed: {exc}")

            # 3. Build System Prompt
            system_prompt = build_roleplay_prompt(
                persona=persona,
                contact_name=target.username or "friend",
                intel=intel_list,
                week=chat.current_week,
                selected_lore=selected_lore,
                goal=chat.goal or ""
            )

            # Inject Communication Style Mirroring instructions if profile exists
            if mirror_profile:
                style_str = json.dumps(mirror_profile, indent=2)
                system_prompt += (
                    "\n\n### COMMUNICATION STYLE MIRRORING PROFILE ###\n"
                    "Match the user's communication style formatting and mannerisms based on this profile:\n"
                    f"{style_str}\n"
                )

            # 4. Format history list & Call Groq
            history_payload = [
                {"role": m.role, "content": m.content}
                for m in recent_msgs
            ]
            history_payload.append({"role": "user", "content": inbound_message})

            # System prompt instruction forcing strict JSON format
            json_system_prompt = (
                system_prompt + "\n\n"
                "### OUTPUT FORMAT REQUIREMENT ###\n"
                "You MUST output your response as a valid JSON object ONLY. No markdown, no commentary outside JSON.\n"
                "JSON Schema:\n"
                "{\n"
                '  "intent": "Explain in 1-2 sentences your psychological strategy for this reply.",\n'
                '  "confidence_score": 85,\n'
                '  "needs_human": false,\n'
                '  "message": "Your actual text message response to the user."\n'
                "}"
            )

            raw_response = await groq_client.chat_complete_with_history(
                system_prompt=json_system_prompt,
                messages_history=history_payload
            )

            # 5. Parse JSON response safely
            parsed_res = RelationshipService._parse_ai_response(raw_response)
            intent_text = parsed_res["intent"]
            confidence_score = parsed_res["confidence_score"]
            needs_human = parsed_res["needs_human"]
            reply_text = parsed_res["message"]

            # 6. Save user message to DB
            await relationship_messages_repo.add_message(
                session=session,
                chat_id=chat.id,
                role="user",
                content=inbound_message
            )

            # 7. Save assistant message to DB
            asst_msg = await relationship_messages_repo.add_message(
                session=session,
                chat_id=chat.id,
                role="assistant",
                content=reply_text
            )

            # 8. Log AI intent
            await intents_repo.log_intent(
                session=session,
                message_id=asst_msg.id,
                intent_text=intent_text,
                confidence_score=confidence_score,
                needs_human=needs_human
            )

            await session.commit()

            # 9. Background: Fire Intel Extraction (non-blocking)
            asyncio.create_task(
                RelationshipService._extract_and_save_intel(
                    target_id=target_id,
                    inbound_message=inbound_message,
                    contact_name=target.username or "friend"
                )
            )

            # 10. If human override requested, log and stop execution
            if needs_human:
                logger.warning(
                    f"[RELATIONSHIP_SERVICE] 🚨 Human override requested for target @{target.username}. "
                    f"Confidence: {confidence_score}. Intent: {intent_text}"
                )
                return {
                    "status": "needs_human",
                    "intent": intent_text,
                    "confidence_score": confidence_score,
                    "reply_text": reply_text
                }

            # 11. Send reply via Mister Simulator
            try:
                logger.info(f"[RELATIONSHIP_SERVICE] Sending response to @{target.username} via Simulator...")
                send_result = await simulator_client.send_dm(
                    session_name=session_name,
                    target_username=target.username,
                    message_text=reply_text,
                    telegram_user_id=target.telegram_user_id
                )
                logger.info(f"[RELATIONSHIP_SERVICE] Simulator DM sent result: {send_result}")
            except Exception as send_exc:
                logger.error(f"[RELATIONSHIP_SERVICE] Failed to send Simulator DM to @{target.username}: {send_exc}")

            return {
                "status": "sent",
                "intent": intent_text,
                "confidence_score": confidence_score,
                "reply_text": reply_text
            }

    @staticmethod
    def _parse_ai_response(raw: str) -> dict:
        """Safely parses Groq's JSON string response into dict fields."""
        fallback = {
            "intent": "Standard conversation response.",
            "confidence_score": 75,
            "needs_human": False,
            "message": raw.strip()
        }
        if not raw:
            return fallback

        cleaned = raw.strip()
        if "```" in cleaned:
            lines = [l for l in cleaned.splitlines() if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                # Safely parse confidence_score float/int
                conf_raw = data.get("confidence_score", 75)
                try:
                    conf = int(float(conf_raw))
                except Exception:
                    conf = 75

                msg = str(data.get("message", "")).strip() or raw.strip()
                intent = str(data.get("intent", "No explicit intent provided.")).strip()
                needs_human = bool(data.get("needs_human", False))

                return {
                    "intent": intent,
                    "confidence_score": conf,
                    "needs_human": needs_human,
                    "message": msg
                }
        except Exception as exc:
            logger.warning(f"[RELATIONSHIP_SERVICE] Failed to parse Groq JSON response ({exc}). Using fallback.")

        return fallback

    @staticmethod
    async def _extract_and_save_intel(target_id: int, inbound_message: str, contact_name: str) -> None:
        """Fire-and-forget background task to extract intel from inbound message."""
        try:
            prompt = build_intel_extraction_prompt(contact_name)
            raw_intel = await groq_client.chat_complete(
                system_prompt=prompt,
                user_prompt=inbound_message
            )
            entries = parse_intel_response(raw_intel)
            if entries:
                async with AsyncSessionLocal() as session:
                    added = await intel_repo.bulk_add_intel(session, target_id, entries, source="chat")
                    await session.commit()
                    logger.info(f"[INTEL_EXTRACTOR] Extracted and saved {added} intel entries for target ID {target_id}")
        except Exception as exc:
            logger.warning(f"[INTEL_EXTRACTOR] Background intel extraction error for target ID {target_id}: {exc}")
