import datetime
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from data.repositories import story_arc_repo
from clients.simulator_client import simulator_client

logger = logging.getLogger(__name__)

class ArcService:
    """
    Orchestrates Story Arc narrative progression and media injection for active leads.
    Purely event-driven — runs once per inbound reply.
    """

    @staticmethod
    async def check_and_advance(
        session: AsyncSession,
        target,
        persona_id: int,
        session_name: str | None = None
    ) -> Optional[str]:
        """
        Calculates elapsed days since target.replied_at (or created_at), determines
        if target qualifies for an advanced chapter, fires media attachments via
        Simulator, updates target.arc_chapter, and returns the chapter's theme_text for Groq.
        """
        if not persona_id:
            return None

        # 1. Fetch all story arc chapters for this persona
        arcs = await story_arc_repo.get_arcs_for_persona(session, persona_id)
        if not arcs:
            return None # Persona has no active story arc configured

        # 2. Calculate days elapsed since first reply (or creation)
        reference_time = getattr(target, "replied_at", None) or getattr(target, "created_at", None)
        if not reference_time:
            days_elapsed = 0
        else:
            now = datetime.datetime.now(datetime.timezone.utc)
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=datetime.timezone.utc)
            days_elapsed = (now - reference_time).days

        # 3. Find highest earned chapter (delay_days <= days_elapsed)
        earned_arc = None
        for arc in arcs:
            if arc.delay_days <= days_elapsed:
                earned_arc = arc
            else:
                break # Since arcs are sorted by chapter_number asc

        if not earned_arc:
            return None

        current_chapter = getattr(target, "arc_chapter", 0)

        # 4. Check if target has advanced to a new chapter
        if earned_arc.chapter_number <= current_chapter:
            # Already at or past this chapter — return active chapter theme without re-firing media
            active_arc = await story_arc_repo.get_arc_by_chapter(session, persona_id, current_chapter)
            return active_arc.theme_text if active_arc else None

        # 5. Check media requirements: If chapter has media but session_name is missing, defer advance
        media_items = await story_arc_repo.get_chapter_media(session, earned_arc.id)
        if media_items and not session_name:
            logger.warning(
                f"[ARC_SERVICE] Target @{target.username} qualifies for Chapter {earned_arc.chapter_number}, "
                f"but session_name is missing. Deferring chapter advance until session is assigned."
            )
            active_arc = await story_arc_repo.get_arc_by_chapter(session, persona_id, current_chapter)
            return active_arc.theme_text if active_arc else None

        # 6. Fire attached chapter media via Simulator (best-effort, track success)
        all_media_ok = True
        if media_items and session_name:
            for item in media_items:
                try:
                    logger.info(
                        f"[ARC_SERVICE] Firing chapter media ({item.media_type}) to @{target.username} "
                        f"via session '{session_name}' (file_id: {item.telegram_file_id[:10]}...)"
                    )
                    res = await simulator_client.send_media(
                        session_name=session_name,
                        target_username=target.username,
                        telegram_file_id=item.telegram_file_id,
                        media_type=item.media_type,
                        telegram_user_id=getattr(target, "telegram_user_id", None)
                    )
                    if not (isinstance(res, dict) and (res.get("status") == "success" or res.get("ok", False))):
                        logger.error(f"[ARC_SERVICE] Media send returned non-ok status for @{target.username}: {res}")
                        all_media_ok = False
                except Exception as media_exc:
                    logger.error(
                        f"[ARC_SERVICE] Failed to send media file_id {item.telegram_file_id} to @{target.username}: {media_exc}"
                    )
                    all_media_ok = False

        if not all_media_ok:
            logger.warning(
                f"[ARC_SERVICE] One or more media items failed to send for @{target.username}. "
                f"Chapter advance deferred so media delivery can be retried later."
            )
            active_arc = await story_arc_repo.get_arc_by_chapter(session, persona_id, current_chapter)
            return active_arc.theme_text if active_arc else None

        # 7. Media delivery succeeded (or chapter has no media): Advance target.arc_chapter IN-MEMORY.
        # RelationshipService owns the session and will commit this atomically at the end of the reply cycle.
        logger.info(
            f"[ARC_SERVICE] Target @{target.username} (ID: {target.id}) advanced "
            f"from Chapter {current_chapter} -> Chapter {earned_arc.chapter_number} "
            f"(Days active: {days_elapsed})"
        )
        target.arc_chapter = earned_arc.chapter_number
        return earned_arc.theme_text
