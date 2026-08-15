from core.schemas.subscriptions import SubscriptionAddSchema
from core.models.subscriptions import SubscriptionsModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from datetime import datetime

from core.utils.states import SubscriptionStatus


class SubscriptionsRepository:
    @classmethod
    async def create_subscription(cls, sub_data: SubscriptionAddSchema, session: AsyncSession):
        subscription_data = sub_data.model_dump()

        subscription = SubscriptionsModel(**subscription_data)

        session.add(subscription)

        await session.commit()
        await session.refresh(subscription)

        return {'success': True, 'data': subscription.id}


    @classmethod
    async def get_user_subscriptions(cls, tg_id: int, session: AsyncSession):
        query = select(SubscriptionsModel).where(SubscriptionsModel.tg_id == tg_id)

        resp = await session.execute(query)

        sub = resp.scalars().all()

        if sub:
            return  {'success': True, 'data': sub}
        return  {'success': False}

    
    @classmethod
    async def get_all_expired_subs(cls, session: AsyncSession, now: datetime):
        query = select(SubscriptionsModel).where(
                SubscriptionsModel.status == SubscriptionStatus.ACTIVE,
                SubscriptionsModel.end_date <= now,
            )

        resp = await session.execute(query)

        subs = resp.scalars().all()

        return {'success': True, 'data': subs}


    @classmethod 
    async def get_all_active_subs(cls, session: AsyncSession):
        query = select(SubscriptionsModel).where(
                        SubscriptionsModel.status == SubscriptionStatus.ACTIVE
                    )
        
        resp = await session.execute(query)
        
        subs = resp.scalars().all()
        
        return {'success': True, 'data': subs}


    @classmethod
    async def get_subscription_data(cls, sub_id: int, session: AsyncSession):
        query = select(SubscriptionsModel).where(SubscriptionsModel.id == sub_id)

        resp = await session.execute(query)

        data = resp.scalars().first()

        return {'success': True, 'data': data}


    @classmethod
    async def get_subscription_by_uuid(cls, uuid: str, session: AsyncSession):
        query = select(SubscriptionsModel).where(SubscriptionsModel.uuid == uuid)
        
        resp = await session.execute(query)
        
        data = resp.scalars().first()
        
        return {'success': True, 'data': data}


    @classmethod
    async def update_subscription_status(cls, sub_id: int, status: str, session: AsyncSession):
        query = update(SubscriptionsModel).where(SubscriptionsModel.id == sub_id).values(status=status)

        await session.execute(query)

        return {'success': True, 'data': None}


    @classmethod
    async def update_subscription_end_date(cls, sub_id: int, new_end_date: datetime, session: AsyncSession):
        query = update(SubscriptionsModel).where(SubscriptionsModel.id == sub_id).values(end_date=new_end_date)

        await session.execute(query)

        await session.commit()

        return {'success': True, 'data': None}


    @classmethod
    async def get_expired_subscriptions(cls, session: AsyncSession):
        query = select(SubscriptionsModel).where(SubscriptionsModel.status == SubscriptionStatus.EXPIRED)

        data = await session.execute(query)

        res = data.scalars().all()

        return {'success': True, 'data': res}


    @classmethod
    async def delete_expired_subscription(cls, sub_id: int, session: AsyncSession):
        query = delete(SubscriptionsModel).where(SubscriptionsModel.id == sub_id)

        await session.execute(query)

        await session.commit()

        return {'success': True, 'data': None}


    @classmethod
    async def get_longest_active_subscription(cls, tg_id: int, session: AsyncSession,):
        query = (
            select(SubscriptionsModel)
            .where(
                SubscriptionsModel.tg_id == tg_id,
                SubscriptionsModel.status == SubscriptionStatus.ACTIVE,
                SubscriptionsModel.end_date > datetime.now(),
            )
            .order_by(SubscriptionsModel.end_date.desc())
            .limit(1)
        )

        result = await session.execute(query)

        data = result.scalar_one_or_none()

        return {'success': True, 'data': data}