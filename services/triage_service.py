import asyncio
import logging
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from core.triage_engine import TriageEngine
from providers.groq_client import groq_client
from services.handoff_service import HandoffService

logger = logging.getLogger(__name__)

class TriageService:
    """
    Orchestrates AI lead classification using Groq LLM and editable prompts.
    Trigger auto-handoff initiation for RELATIONAL leads.
    """

    @staticmethod
    async def classify_lead(target_id: int, chat_history: str) -> str:
        """
        Classifies a lead into TRANSACTIONAL, RELATIONAL, or DEAD.
        Saves triage_status and triage_raw_chat to database.
        If RELATIONAL, automatically kicks off HandoffService.
        """
        async with AsyncSessionLocal() as session:
            target = await target_repo.get_target_by_id(session, target_id)
            if not target:
                logger.error(f"[TRIAGE_SERVICE] Target ID {target_id} not found for triage.")
                return "UNCLASSIFIED"

            # 1. Load active system prompt
            prompt_data = TriageEngine.load_prompt()
            system_prompt = prompt_data.get("system_prompt", "")

            # 2. Build user prompt (inject profile_notes if confidence >= 2)
            user_prompt_parts = []
            if getattr(target, "profile_notes", None) and getattr(target, "profile_confidence", 0) >= 2:
                user_prompt_parts.append(f"Target Profile Intel: {target.profile_notes}")
            
            user_prompt_parts.append(f"Recent Chat History:\n{chat_history}")
            user_prompt = "\n\n".join(user_prompt_parts)

            # 3. Call Groq API Provider
            try:
                raw_response = await groq_client.chat_complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                )
                
                # Parse single word verdict
                verdict = raw_response.strip().upper()
                if "TRANSACTIONAL" in verdict:
                    classification = "TRANSACTIONAL"
                elif "RELATIONAL" in verdict:
                    classification = "RELATIONAL"
                elif "DEAD" in verdict:
                    classification = "DEAD"
                else:
                    classification = "UNCLASSIFIED"

                logger.info(f"[TRIAGE_SERVICE] Classified target {target.username} as '{classification}'")

                # 4. Save to Database
                await target_repo.update_triage(
                    session=session,
                    target_id=target_id,
                    triage_status=classification,
                    raw_chat=chat_history[:500]
                )
                await session.commit()

                # 5. Auto-Handoff Trigger for RELATIONAL leads
                if classification == "RELATIONAL":
                    logger.info(f"[TRIAGE_SERVICE] RELATIONAL verdict detected. Triggering HandoffService for @{target.username}...")
                    asyncio.create_task(HandoffService.initiate_handoff(target_id))

                return classification

            except Exception as e:
                logger.error(f"[TRIAGE_SERVICE] Exception during triage for target {target.username}: {e}")
                return "UNCLASSIFIED"
