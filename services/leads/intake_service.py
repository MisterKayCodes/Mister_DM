import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from data.database import AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from data.models.campaign import Campaign

logger = logging.getLogger(__name__)

class IntakeService:
    """
    Service layer handling single and bulk lead intake from Mister Profiler.
    Enforces atomic merge strategies to prevent double-DMs or status resets.
    """

    @staticmethod
    async def find_campaign_for_group(source_group: str, session: Optional[AsyncSession] = None) -> Optional[int]:
        """
        Looks up an active campaign matching the given source_group (e.g. @BinanceSignals).
        Falls back to the first available active campaign if no exact group match exists.
        """
        clean_group = source_group.strip() if source_group else None
        if not clean_group:
            return None

        async def _lookup(sess: AsyncSession) -> Optional[int]:
            stmt = select(Campaign).where(
                (Campaign.name.ilike(f"%{clean_group}%")) | (Campaign.name.ilike(f"%{clean_group.lstrip('@')}%"))
            ).limit(1)
            res = await sess.execute(stmt)
            c = res.scalar_one_or_none()
            if c:
                return c.id

            campaigns = await campaign_repo.get_all_campaigns(sess)
            if campaigns:
                return campaigns[0].id
            return None

        if session:
            return await _lookup(session)
        else:
            async with AsyncSessionLocal() as sess:
                return await _lookup(sess)

    @staticmethod
    async def process_single(
        campaign_id: int,
        username: str,
        telegram_user_id: Optional[int] = None,
        source_group: Optional[str] = None,
        profile_notes: Optional[str] = None,
        profile_confidence: Optional[int] = 0,
        session: Optional[AsyncSession] = None
    ) -> dict:
        """
        Processes a single lead intake.
        If lead is new: creates target and assigns profile intel.
        If lead exists: merges profile notes, upgrades confidence, fills source_group without touching status.
        """
        clean_user = username.lstrip("@").strip()
        
        async def _execute(sess: AsyncSession) -> dict:
            existing = await target_repo.get_target_by_campaign_and_username(sess, campaign_id, clean_user)
            
            if not existing:
                # 1. Create new target
                await target_repo.add_targets_bulk(sess, campaign_id, [clean_user])
                await sess.flush()
                
                target = await target_repo.get_target_by_campaign_and_username(sess, campaign_id, clean_user)
                if target:
                    await target_repo.update_profile(
                        session=sess,
                        target_id=target.id,
                        profile_notes=profile_notes,
                        profile_confidence=profile_confidence or 0,
                        source_group=source_group
                    )
                    if telegram_user_id:
                        target.telegram_user_id = telegram_user_id
                    await sess.flush()
                    return {"result": "created", "lead_id": target.id, "username": clean_user}
                return {"result": "created", "lead_id": None, "username": clean_user}
            else:
                # 2. Merge existing target (NEVER overwrite status to prevent double-DMs)
                new_confidence = max(existing.profile_confidence or 0, profile_confidence or 0)
                notes_to_use = profile_notes if profile_notes else existing.profile_notes
                source_to_use = source_group if (source_group and not existing.source_group) else existing.source_group
                
                await target_repo.update_profile(
                    session=sess,
                    target_id=existing.id,
                    profile_notes=notes_to_use,
                    profile_confidence=new_confidence,
                    source_group=source_to_use
                )
                if telegram_user_id and not existing.telegram_user_id:
                    existing.telegram_user_id = telegram_user_id
                    
                await sess.flush()
                return {"result": "merged", "lead_id": existing.id, "username": clean_user}

        if session:
            return await _execute(session)
        else:
            async with AsyncSessionLocal() as sess:
                res = await _execute(sess)
                await sess.commit()
                return res

    @staticmethod
    async def process_bulk(leads: list[dict]) -> dict:
        """
        Processes a batch list of lead intake items inside a single DB transaction session.
        Returns summary counts: created, merged, failed.
        """
        created_count = 0
        merged_count = 0
        failed_count = 0

        async with AsyncSessionLocal() as session:
            for item in leads:
                try:
                    campaign_id = item.get("campaign_id")
                    source_group = item.get("source_group")

                    # Auto-match campaign if campaign_id missing
                    if not campaign_id and source_group:
                        campaign_id = await IntakeService.find_campaign_for_group(source_group, session=session)

                    if not campaign_id:
                        logger.warning(f"[INTAKE_SERVICE] Skipped lead '{item.get('username')}' — no valid campaign_id or source_group.")
                        failed_count += 1
                        continue

                    res = await IntakeService.process_single(
                        campaign_id=campaign_id,
                        username=item.get("username", ""),
                        telegram_user_id=item.get("telegram_user_id"),
                        source_group=source_group,
                        profile_notes=item.get("profile_notes"),
                        profile_confidence=item.get("profile_confidence", 0),
                        session=session
                    )

                    if res.get("result") == "created":
                        created_count += 1
                    elif res.get("result") == "merged":
                        merged_count += 1

                except Exception as e:
                    logger.error(f"[INTAKE_SERVICE] Error processing bulk lead '{item.get('username')}': {e}")
                    failed_count += 1

            await session.commit()

        return {
            "total": len(leads),
            "created": created_count,
            "merged": merged_count,
            "failed": failed_count
        }
