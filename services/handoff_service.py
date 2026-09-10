import logging
from sqlalchemy.sql import func
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from clients.mister_ai_client import mister_ai_client
from clients.exceptions import APIUnavailableError, APIResponseError

logger = logging.getLogger(__name__)

class HandoffService:
    """
    Manages lead transfer lifecycle from Mister DM to Mister AI.
    Handles pending approval states, payload packaging, and failed retry recovery.
    Enforces DB Session boundaries OUTSIDE network calls to prevent SQLite locks.
    """

    @staticmethod
    async def initiate_handoff(target_id: int, auto_approve: bool = False) -> str:
        """
        Initiates handoff for a target.
        Enforces human approval by default: status becomes 'pending'.
        If auto_approve is explicitly set to True, executes handoff immediately.
        Returns the new handoff_status.
        """
        async with AsyncSessionLocal() as session:
            target = await target_repo.get_target_by_id(session, target_id)
            if not target:
                logger.error(f"[HANDOFF_SERVICE] Target ID {target_id} not found.")
                return "unknown"

            # Always default to 'pending' unless explicitly auto_approved
            new_status = "approved" if auto_approve else "pending"
            target.handoff_status = new_status
            await session.commit()
            logger.info(f"[HANDOFF_SERVICE] Initiated handoff for @{target.username} (Status: {new_status})")

        if auto_approve:
            success, _ = await HandoffService.execute_handoff(target_id)
            return "sent" if success else "handoff_failed"

        return "pending"

    @staticmethod
    async def execute_handoff(target_id: int) -> tuple[bool, str]:
        """
        Executes HTTP payload transfer to Mister AI (POST /api/v1/leads/intake).
        CRITICAL ARCHITECTURE: The network call is performed 100% OUTSIDE database sessions
        to prevent holding SQLite write locks over network round trips.
        """
        payload = None

        # -------------------------------------------------------------
        # STEP 1: READ + INCREMENT ATTEMPTS (DB Session 1 - Closes Fast)
        # -------------------------------------------------------------
        async with AsyncSessionLocal() as session:
            target = await target_repo.get_target_by_id(session, target_id)
            if not target:
                return False, "Target not found"

            # Package full lead intelligence payload
            payload = {
                "source_bot": "Mister_DM",
                "campaign_id": target.campaign_id,
                "username": target.username,
                "telegram_user_id": target.telegram_user_id,
                "source_group": getattr(target, "source_group", None),
                "profile_notes": getattr(target, "profile_notes", None),
                "profile_confidence": getattr(target, "profile_confidence", 0),
                "triage_status": getattr(target, "triage_status", "RELATIONAL"),
                "triage_raw_chat": getattr(target, "triage_raw_chat", None)
            }

            target.handoff_attempts = (getattr(target, "handoff_attempts", 0) or 0) + 1
            target.handoff_last_attempt = func.now()
            await session.commit()
            # DB Session 1 closes HERE ↑

        # -------------------------------------------------------------
        # STEP 2: NETWORK CALL TO MISTER AI (100% Outside DB Session!)
        # -------------------------------------------------------------
        success = False
        error_msg = None

        try:
            res = await mister_ai_client.intake_lead(payload)
            success = res.get("status") == "success" or res.get("ok", False)
            if not success:
                error_msg = f"Mister AI returned error: {res}"
        except (APIUnavailableError, APIResponseError, Exception) as e:
            success = False
            error_msg = f"Transfer failed: {str(e)}"
            logger.error(f"[HANDOFF_SERVICE] Failed to transfer @{payload['username']} to Mister AI: {e}")

        # -------------------------------------------------------------
        # STEP 3: WRITE FINAL HANDOFF RESULT (DB Session 2 - Closes Fast)
        # -------------------------------------------------------------
        async with AsyncSessionLocal() as session:
            target = await target_repo.get_target_by_id(session, target_id)
            if target:
                target.handoff_status = "sent" if success else "handoff_failed"
                await session.commit()

        if success:
            logger.info(f"[HANDOFF_SERVICE] Successfully transferred @{payload['username']} to Mister AI!")
            return True, "Handoff completed successfully"
        else:
            return False, error_msg or "Handoff failed"

    @staticmethod
    async def retry_failed_handoffs() -> int:
        """
        Retries all leads currently marked as 'handoff_failed'.
        Returns count of successfully retried leads.
        """
        async with AsyncSessionLocal() as session:
            failed_targets = await target_repo.get_failed_handoffs(session)
            target_ids = [t.id for t in failed_targets]

        success_count = 0
        for tid in target_ids:
            ok, _ = await HandoffService.execute_handoff(tid)
            if ok:
                success_count += 1

        logger.info(f"[HANDOFF_SERVICE] Retried {len(target_ids)} failed handoffs. Successes: {success_count}")
        return success_count
