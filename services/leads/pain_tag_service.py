from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from data.database import AsyncSessionLocal
from data.repositories import pain_tag_repo
import logging

logger = logging.getLogger(__name__)

class PainTagService:
    """
    Coordinates business logic for Pain Points, isolating the Mouth from the Memory layer.
    """

    @staticmethod
    async def get_all_pain_tags_with_counts(session: AsyncSession = None) -> list[dict]:
        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await pain_tag_repo.get_all_pain_tags_with_counts(new_sess)
        return await pain_tag_repo.get_all_pain_tags_with_counts(session)

    @staticmethod
    async def create_pain_tag(name: str, session: AsyncSession = None) -> dict:
        """
        Validates name, normalizes it, and manages the get-or-create transaction.
        """
        async def _execute(sess: AsyncSession):
            display_name = name.strip()
            if not display_name:
                return {"success": False, "message": "Pain point name cannot be empty."}
                
            name_normalized = display_name.lower()
            
            # Check if exists
            existing = await pain_tag_repo.get_pain_tag_by_name(sess, name_normalized)
            if existing:
                return {
                    "success": True, 
                    "data": {
                        "id": existing.id,
                        "display_name": existing.display_name,
                        "created_at": existing.created_at
                    }
                }
                
            # Create new
            try:
                tag = await pain_tag_repo.insert_pain_tag(sess, name_normalized, display_name)
                return {
                    "success": True,
                    "data": {
                        "id": tag.id,
                        "display_name": tag.display_name,
                        "created_at": tag.created_at
                    }
                }
            except IntegrityError:
                # Race condition: another transaction created it just now
                existing = await pain_tag_repo.get_pain_tag_by_name(sess, name_normalized)
                return {
                    "success": True, 
                    "data": {
                        "id": existing.id,
                        "display_name": existing.display_name,
                        "created_at": existing.created_at
                    }
                }

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    res = await _execute(new_sess)
                    if res["success"]:
                        await new_sess.commit()
                    return res
                except Exception as e:
                    await new_sess.rollback()
                    logger.error(f"Failed to create pain tag: {e}")
                    return {"success": False, "message": str(e)}
        return await _execute(session)

    @staticmethod
    async def get_targets_for_pain_tag(pain_tag_id: int, session: AsyncSession = None) -> list[dict]:
        async def _execute(sess: AsyncSession):
            targets = await pain_tag_repo.get_targets_for_pain_tag(sess, pain_tag_id)
            return [
                {
                    "id": t.id,
                    "username": t.username,
                    "status": t.status,
                    "note": t.note
                } for t in targets
            ]
            
        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def tag_target(target_id: int, pain_tag_id: int, session: AsyncSession = None) -> dict:
        async def _execute(sess: AsyncSession):
            try:
                await pain_tag_repo.tag_target(sess, target_id, pain_tag_id)
                return {"success": True}
            except IntegrityError:
                # Already tagged
                return {"success": False, "message": "Target is already assigned this pain tag."}

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    res = await _execute(new_sess)
                    if res["success"]:
                        await new_sess.commit()
                    return res
                except Exception as e:
                    await new_sess.rollback()
                    return {"success": False, "message": str(e)}
        return await _execute(session)
