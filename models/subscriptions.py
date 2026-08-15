from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from database import Model
from datetime import datetime
from core.utils.states import SubscriptionStatus


class SubscriptionsModel(Model):
    __tablename__ = 'clients'

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    tg_id: Mapped[int] 
    
    uuid: Mapped[str]

    tarif: Mapped[str]

    period_start: Mapped[datetime]

    start_date: Mapped[datetime]
    end_date: Mapped[datetime]

    status: Mapped[SubscriptionStatus]

