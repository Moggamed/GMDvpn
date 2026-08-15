from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from sqlalchemy.ext.asyncio import AsyncSession

from core.repository.users import UsersRepository


class BlockedUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        session: AsyncSession = data["session"]

        user = data.get("event_from_user")

        if not user:
            return await handler(event, data)

        user_data = (await UsersRepository.get_user_with_tg_id(
            user.id,
            session,
        ))['data']

        if user_data and user_data.is_blocked:
            return

        return await handler(event, data)