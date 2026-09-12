from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from data.models.mirror_observation_buffer import MirrorObservationBuffer

class MirrorObservationsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_observation(
        self,
        target_id: int,
        message_text: str,
        relationship_message_id: Optional[int] = None
    ) -> MirrorObservationBuffer:
        observation = MirrorObservationBuffer(
            target_id=target_id,
            message_text=message_text,
            relationship_message_id=relationship_message_id,
            is_analyzed=False
        )
        self.session.add(observation)
        await self.session.flush()
        return observation

    async def get_pending_observations(self, target_id: int) -> List[MirrorObservationBuffer]:
        stmt = (
            select(MirrorObservationBuffer)
            .where(
                MirrorObservationBuffer.target_id == target_id,
                MirrorObservationBuffer.is_analyzed == False,
                MirrorObservationBuffer.analysis_batch_id.is_(None)
            )
            .order_by(MirrorObservationBuffer.observed_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def claim_pending_batch(self, target_id: int, batch_id: str) -> List[MirrorObservationBuffer]:
        """
        Atomically claims all un-analyzed, un-claimed pending observations for a target.
        Returns the list of claimed observations.
        """
        pending = await self.get_pending_observations(target_id)
        if not pending:
            return []

        pending_ids = [obs.id for obs in pending]
        stmt = (
            update(MirrorObservationBuffer)
            .where(MirrorObservationBuffer.id.in_(pending_ids))
            .values(analysis_batch_id=batch_id)
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Return updated objects
        stmt_refetch = (
            select(MirrorObservationBuffer)
            .where(MirrorObservationBuffer.analysis_batch_id == batch_id)
            .order_by(MirrorObservationBuffer.observed_at.asc())
        )
        res = await self.session.execute(stmt_refetch)
        return list(res.scalars().all())

    async def mark_batch_analyzed(self, batch_id: str) -> None:
        stmt = (
            update(MirrorObservationBuffer)
            .where(MirrorObservationBuffer.analysis_batch_id == batch_id)
            .values(is_analyzed=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()
