from aiogram import F, Router
from aiogram.filters import StateFilter, CommandObject, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils import deep_linking
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.filters.isNewUser import isNewUser
from core.filters.isHaveFree import isHaveFree
from core.filters.isPaid import isPaid
from core.filters.isFirstUse import isFirstUse
from core.filters.isAdmin import isAdmin
from core.filters.isHisKey import isHisKey

from core.repository.users import UsersRepository
from core.repository.subscriptions import SubscriptionsRepository
from core.repository.promocodes import PromocodesRepository
from core.repository.used_promo import UsedPromoRepository
from core.repository.payments import PaymentsRepository

from core.schemas.users import UserAddSchema
from core.schemas.used_promo import UsedPromoAddSchema
from core.schemas.payments import PaymentsAddSchema

from core.keyboards.user_kb import *
from core.keyboards.subs_kb import periods_kb, tarifs_kb
from core.keyboards.admin_kb import *

from core.utils.create_client import create_user_vless_key
from core.utils.states import States, SubscriptionStatus, PaymentStatus
from core.utils.extend_sub import extend_sub, add_referral_days
from core.utils.states import Languages
from core.utils.end_date_formatting import date_to_str
from core.utils.get_client_sub import generate_link

from core.locales.get_texts import get_text

from config import *

router = Router()

@router.message(CommandStart())
async def start_message(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession,):
    tg_id = message.from_user.id
    bot = message.bot


    if not await isNewUser(tg_id, session):
        if isAdmin(tg_id):
                        await message.answer(
                            get_text('START_ADMIN'),
                            reply_markup=admin_start_kb(),
                        )
                        return
        await state.clear()

        have_free_trial = await isHaveFree(tg_id, session)

        await message.answer(
            get_text('MAIN_MENU'),
            reply_markup=start_kb(have_free_trial),
        )
        return


    name = message.from_user.first_name
    username = message.from_user.username

    from_tg_id = None

    if command.args:
        try:
            from_tg_id = int(command.args)
        except ValueError:
            from_tg_id = None

    user = UserAddSchema(
        name=name,
        username=username,
        tg_id=tg_id,
        from_tg_id=from_tg_id,
        language=Languages.RU
    )

    await UsersRepository.create_user_profile(
        user,
        session,
    )

    

    if from_tg_id:

        if from_tg_id == tg_id:

            await bot.send_message(
                ADMIN_ID,
                get_text('START_SELF_REF_ADMIN', name=name),
            )

        else:

            referrer = (await UsersRepository.get_user_with_tg_id(
                from_tg_id,
                session,
            ))['data']

            if referrer:

                await UsersRepository.update_refs_count(
                    from_tg_id,
                    session,
                )

                await UsersRepository.set_user_active(
                    from_tg_id,
                    session,
                )

                await bot.send_message(
                    ADMIN_ID,
                    get_text('START_REFERRAL_ADMIN', name=name, referrer_id=from_tg_id),
                )

                sub = await add_referral_days(
                    from_tg_id,
                    session,
                )

                if sub is None:
                    key = await create_user_vless_key(
                        from_tg_id,
                        session,
                        "free",
                        BONUS_PER_REF,
                        20,
                        1,
                        "days",
                    )

                    await bot.send_message(
                        from_tg_id,
                        get_text('REFERRAL_NEW_KEY', days=BONUS_PER_REF, key=key),
                        reply_markup=instructions_kb(True),
                    )

                else:

                    await extend_sub(
                        sub.id,
                        sub.uuid,
                        sub.end_date,
                        BONUS_PER_REF,
                        session,
                        sub.tarif,
                        "days",
                    )

                    await bot.send_message(
                        from_tg_id,
                        get_text('REFERRAL_NEW_USER', days=BONUS_PER_REF, sub_id=sub.id),
                        reply_markup=start_kb(),
                    )

            else:

                await bot.send_message(
                    ADMIN_ID,
                    get_text('START_INVALID_REF_ADMIN', name=name, referred_id=from_tg_id),
                )

    else:

        await bot.send_message(
            ADMIN_ID,
            get_text('START_ADMIN_NEW_USER', name=name),
        )

    await message.answer(
        get_text('WELCOME'),
        reply_markup=start_kb(True),
    )        

# =========================== BUY VPN ==============================================


@router.callback_query(F.data == 'buy_vpn_button')
async def buy_vpn_pressed(callback: CallbackQuery):
    await callback.message.edit_text(get_text('CHOOSE_TARIF'),
                                    reply_markup=tarifs_kb)
    

@router.callback_query(F.data.startswith('tarif='))
async def tarif_selected(callback: CallbackQuery, state: FSMContext):
    tarif = callback.data.split('=')[1]
    buy_type = 'buy'
    await state.set_state(States.tarif_selected)
    await state.update_data(tarif=tarif, buy_type=buy_type)

    await callback.message.edit_text(get_text('CHOOSE_PERIOD'),
                                    reply_markup=periods_kb(tarif))
    

@router.callback_query(F.data.startswith('sub_period='))
async def period_selected(callback: CallbackQuery, state: FSMContext):
    period = int(callback.data.split('=')[1])

    await state.set_state(States.promo_waiting)

    await state.update_data(period=period)

    await callback.message.edit_text(get_text('ENTER_PROMO'),
                                        reply_markup=skip_promo_button)


@router.callback_query(F.data == 'skip_promo_button')
async def payment_method_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.edit_text(get_text('CHOOSE_PAYMENT'),
                                        reply_markup=payment_methods_kb)

    
    await state.set_state(States.payment_process)
    await state.update_data(multiplier=None)


@router.message(StateFilter(States.promo_waiting))
async def promo_inputed(message: Message, state: FSMContext, session: AsyncSession):
    promo = message.text

    promo_data = (await PromocodesRepository.get_promo(promo, session))['data']
    promo_data = promo_data[0] if promo_data else None

    if promo_data:
        if promo_data.is_active and promo_data.quantity > 0:
            if promo_data.reusable:
                await PromocodesRepository.update_promo_quantity(promo, session)

                await state.set_state(States.payment_process)
                await state.update_data(multiplier=(1-(promo_data.percentage / 100)), promo=promo)

                await message.answer(get_text('PROMO_ACTIVATED'),
                                    reply_markup=payment_methods_kb)
            else:
                if await isFirstUse(message.from_user.id, promo, session):
                    x = {'used_by': message.from_user.id,
                        'promo': promo,
                        'used_at': datetime.now() + timedelta(hours=3)}
                    used_promo = UsedPromoAddSchema(**x)

                    await PromocodesRepository.update_promo_quantity(promo, session)
                    await UsedPromoRepository.add_used_promo(used_promo, session)

                    await state.set_state(States.payment_process)
                    await state.update_data(multiplier=(1-(promo_data.percentage / 100)), promo=promo)

                    
                    await message.answer(get_text('PROMO_ACTIVATED'),
                                                reply_markup=payment_methods_kb)

                else:
                    await message.answer(get_text('PROMO_ALREADY_USED'),
                                                reply_markup=skip_promo_button)

        else:
            await message.answer(get_text('PROMO_EXHAUSTED'),
                                        reply_markup=skip_promo_button)
    else:
        await message.answer(get_text('PROMO_NOT_FOUND'),
                                    reply_markup=skip_promo_button)


@router.callback_query(F.data.startswith('payment_method='))
async def payment_method_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    state_data = await state.get_data()
    tarif = state_data.get('tarif', None)
    period = state_data.get('period')
    multiplier = state_data.get('multiplier') 
    promo = state_data.get('promo', '')
    multiplier = multiplier if multiplier != None else 1


    if not tarif:
        data = (await SubscriptionsRepository.get_subscription_data(state_data.get('sub_id'), session))['data']
        tarif = data.tarif

    data = PERIODS_PRICE[period][tarif]
    price = int(data['price'] * multiplier)

    method = callback.data.split('=')[1]

    if price == 0:
        user_key = await create_user_vless_key(callback.from_user.id, session,
                                                        tarif, period, data.get('traffic_gb'),
                                                        data.get('devices_limit'))

        await state.set_state(States.default)
        await state.update_data(key=user_key)
        
        await callback.message.edit_text(get_text('PAYMENT_FREE', key=user_key),
                                        reply_markup=instructions_kb(True))
    else:
        dt = datetime.now() + timedelta(hours=3)
        payment = PaymentsAddSchema(tg_id=callback.from_user.id, method=method,
                                    used_promo=promo, amount=price, status=PaymentStatus.EXPIRED, created_at=dt)
        payment_id = (await PaymentsRepository.add_payment(payment, session))['data']

        kb_and_invoice = await invoice_kb(price, callback.from_user.id, method)

        await state.update_data(payment_id=payment_id, invoice_id=kb_and_invoice[1])

        await callback.message.edit_text(get_text('PAYMENT_CRYPTO'), 
                                        reply_markup=kb_and_invoice[0])



@router.callback_query(F.data.startswith('is_paid='))
async def check_is_paid(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    state_data = await state.get_data()
    tarif, period = state_data.get('tarif', None), state_data.get('period'),
    buy_type, sub_id = state_data.get('buy_type'), state_data.get('sub_id')
    user_invoice_id = state_data.get('invoice_id')
    method, callback_invoice_id = callback.data.split('=')[1:]
    if str(user_invoice_id) != callback_invoice_id:
        await callback.message.edit_text(get_text('UNLUCK_PARKER'),
                                         reply_markup=start_kb())
        return

    sub_data = (await SubscriptionsRepository.get_subscription_data(sub_id, session))['data']

    if not tarif:
        tarif = sub_data.tarif

    data = PERIODS_PRICE[period][tarif]

    if await isPaid(method, callback_invoice_id):
        payment_id = state_data.get('payment_id')
        await PaymentsRepository.update_payment_status(payment_id, PaymentStatus.PAID, session)
        if buy_type == 'buy':
            user_key = await create_user_vless_key(callback.from_user.id, session,
                                                tarif, period, data.get('traffic_gb'),
                                                data.get('devices_limit'))
            await callback.message.edit_text(get_text('PAYMENT_SUCCESS', key=user_key),
                                            reply_markup=instructions_kb(True))
            await state.set_state(States.default)
            await state.update_data(key=user_key)
        elif buy_type == 'extend':
            await callback.message.edit_text(get_text('PAYMENT_EXTENDED', sub_id=sub_id),
                                            reply_markup=start_kb()
                                            )
            await extend_sub(sub_id, sub_data.uuid, sub_data.end_date, period, session, sub_data.tarif)
    else:
        await callback.answer(get_text('PAYMENT_NOT_CONFIRMED'), True)


@router.callback_query(F.data.startswith('extend_sub='))
async def extend_sub_pressed(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    sub_id = int(callback.data.split('=')[1])
    sub = (await SubscriptionsRepository.get_subscription_data(sub_id, session))['data']
    if sub.tarif != 'free':
        buy_type = 'extend'

        await state.set_state(States.default)
        await state.update_data(sub_id=sub_id)
        await state.update_data(buy_type=buy_type)

        await callback.message.edit_text(get_text('EXTEND_PERIOD'),
                                        reply_markup=extend_period_kb(sub.tarif))
    else:
        await callback.message.edit_text(get_text('FREE_CANNOT_EXTEND'),
                                        reply_markup=start_kb())


@router.callback_query(F.data.startswith('extend_period='))
async def extend_period_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    sub_id = data.get('sub_id')
    period = int(callback.data.split('=')[1])

    await state.update_data(period=period, sub_id=sub_id)
    
    await state.set_state(States.promo_waiting)
    
    await callback.message.edit_text(get_text('ENTER_PROMO'),
                                            reply_markup=skip_promo_button)


# =========================== FREE TRIAL ============================================


@router.callback_query(F.data == 'free_trial_button')
async def free_trial_button_pressed(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    tg_id = callback.from_user.id
    is_have_free = await isHaveFree(tg_id, session)
    await state.set_state(States.default)

    if is_have_free:
        key = await create_user_vless_key(callback.from_user.id, session, 'free',
                                                FREE_TRIAL, PERIODS_PRICE[1]['free']['traffic_gb'], 
                                                PERIODS_PRICE[1]['free']['devices_limit'], 'days')
        await state.update_data(key=key)
        await UsersRepository.update_have_free_trial(tg_id, session)
        await callback.message.edit_text(get_text('CHOOSE_DEVICE_FOR_INSTRUCTIONS'),
                                        reply_markup=instructions_kb())
    else:
        await callback.message.edit_text(get_text('FREE_TRIAL_ALREADY_USED'),
                                        reply_markup=start_kb())


@router.callback_query(F.data.startswith('device='))
async def device_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    key = data.get('key')
    device = callback.data.split('=')[1]
    await callback.message.answer(get_text('INSTRUCTIONS_FOR_KEY', link=HAPP_LINKS[device], key=key),
                                reply_markup=back_button(), link_preview_options={'is_disabled': True})


@router.callback_query(F.data == 'my_keys_button')
async def my_keys_button_pressed(callback: CallbackQuery, session: AsyncSession):
    get_key_resp = await SubscriptionsRepository.get_user_subscriptions(callback.from_user.id, session)
    if get_key_resp['success']:
        await callback.message.edit_text(get_text('MY_KEYS'),
                                        reply_markup=await user_keys_kb(get_key_resp['data']))
    else:
        await callback.message.edit_text(get_text('NO_ACTIVE_KEYS'),
                                        reply_markup=buy_vpn_button)   


@router.callback_query(F.data.startswith('key_info='))
async def key_info_pressed(callback: CallbackQuery, session: AsyncSession):
    key_id = int(callback.data.split('=')[1])
    if not await isHisKey(key_id, callback.from_user.id, session):
        await callback.message.edit_text(get_text('UNLUCK_PARKER'),
                                         reply_markup=start_kb())
        return

    data = (await SubscriptionsRepository.get_subscription_data(key_id, session))['data']

    status = "🟢" if data.status == SubscriptionStatus.ACTIVE else "🔴"
    end_date = date_to_str(data.end_date)
    tarif = TARIF_TO_TEXT[data.tarif]
    key = generate_link(data.uuid)

    await callback.message.edit_text(get_text('SUBSCRIPTION_INFO', id=data.id, tarif=tarif,
                                                end_date=end_date, status=status, key=key),
                                                reply_markup=extend_sub_kb(data.id, data.tarif))


# ======================= REFERRAL SYSTEM ===========================================

@router.callback_query(F.data == 'ref_system_button')
async def ref_system_button_pressed(callback: CallbackQuery, session: AsyncSession):
    # resp = await UsersRepository.get_user_with_tg_id(callback.from_user.id, session)
    # data = resp['data']
    link = await deep_linking.create_start_link(callback.bot, callback.from_user.id)

    await callback.message.edit_text(get_text('REFERRAL', link=link),
                                    reply_markup=back_button(),)


# =========================== SUPPORT ===============================================

@router.callback_query(F.data == 'support_button')
async def support_button_pressed(callback: CallbackQuery):
    await callback.message.edit_text(get_text('SUPPORT', support_username=SUPPORT_USERNAME),
                                    reply_markup=info_kb)
    

@router.callback_query(F.data.startswith('back_'))
async def back_main_pressed(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    path = callback.data.split('_')[1]
    haveFree = await isHaveFree(callback.from_user.id, session)

    if path == 'main':
        await callback.message.edit_text(get_text('MAIN_MENU'),
                                        reply_markup=start_kb(haveFree) if not isAdmin(callback.from_user.id) else admin_start_kb())
        await state.clear()
    elif path == 'tarifs':
        await callback.message.edit_text(get_text('BACK_TO_TARIFFS'),
                                        reply_markup=tarifs_kb)
        await state.clear()
    elif path == 'paymethods':
        await callback.message.edit_text(get_text('BACK_TO_PAYMENT'),
                                        reply_markup=payment_methods_kb)
    elif path == 'promocodes':
        await callback.message.edit_text(get_text('BACK_TO_PROMOCODES'),
                                        reply_markup=await promocodes_kb(session))
        await state.clear()
    elif path == 'users':
        await callback.message.edit_text(get_text('BACK_TO_USERS'),
                                        reply_markup=await users_kb(1, session))
        