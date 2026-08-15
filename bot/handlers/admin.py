from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from core.utils.states import States
from core.utils.create_client import create_user_vless_key
from core.utils.get_client_sub import get_client_links
from core.utils.schedulers.deactivate_expired_subs import deactivate_expired_subscriptions
from core.utils.schedulers.mail_before_expire import mail_before_expire

from core.filters.isAdmin import isAdmin

from core.schemas.servers import ServerAddSchema
from core.schemas.promocodes import PromoAddSchema

from core.repository.servers import ServersRepository
from core.repository.users import UsersRepository
from core.repository.payments import PaymentsRepository

from core.payments.platega import generate_payment_link_platega, get_payment_status

from core.keyboards.user_kb import start_kb, back_button, invoice_kb
from core.keyboards.admin_kb import *

from core.locales.get_texts import get_text

from config import *


admin_router = Router()


# ----------------- SERVERS ------------------------------


@admin_router.callback_query(F.data == 'add_server_button')
async def create_server(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.input_server_data)
    await callback.message.edit_text(get_text('ADMIN_SERVER_ADD_INSTRUCTION'),
                        reply_markup=back_button())


@admin_router.message(StateFilter(States.input_server_data))
async def get_server_inputed_data(message: Message, state: FSMContext, session: AsyncSession):
    panel_url, name, api_token, inbound_id =  message.text.split('\n')
    data = {
        'panel_url': panel_url,
        'name': name,
        'api_token': api_token,
        'inbound_id': inbound_id
    }

    server = ServerAddSchema(**data)
    server_create_responce = await ServersRepository.create_server(server, session)


    if server_create_responce['success']:
        await message.answer(get_text('ADMIN_SERVER_CREATED'),
                            reply_markup=admin_start_kb())
        await state.clear()
    else:
        await message.answer(get_text('ADMIN_SERVER_CREATE_ERROR'),
                            reply_markup=back_button())


@admin_router.callback_query(F.data.startswith('server='))
async def server_activity_pressed(callback: CallbackQuery, session: AsyncSession):
    server_id, to_do = callback.data.split('=')[1:]
    to_do = True if to_do == 'enable' else False

    await ServersRepository.set_is_active(server_id, to_do, session)

    await callback.message.edit_reply_markup(reply_markup=await servers_kb(session))
        


@admin_router.callback_query(F.data == 'servers_button')
async def servers_button_pressed(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(get_text('ADMIN_SERVERS_LIST'),
                                    reply_markup=await servers_kb(session))
    


# --------------------- PROMOCODES ----------------------------


@admin_router.callback_query(F.data == 'promocodes_button')
async def promocodes_button_pressed(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(get_text('ADMIN_PROMOCODES_LIST'),
                                    reply_markup=await promocodes_kb(session))


@admin_router.callback_query(F.data == 'create_promo_button')
async def create_promo_button_pressed(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(get_text('ADMIN_PROMO_CREATE_INSTRUCTION'),
                                    reply_markup=back_button(path='promocodes'))

    await state.set_state(States.promo_create)


@admin_router.message(StateFilter(States.promo_create))
async def promo_created(message: Message, state: FSMContext, session: AsyncSession):
    try:
        promo, quantity, percentage, reusable = message.text.split('\n')
        reusable = True if reusable != '0' else False
        promo_schema = PromoAddSchema(promo=promo, quantity=quantity, percentage=percentage, reusable=reusable)
        success = (await PromocodesRepository.create_promo(promo_schema, session))['success']

        if success:
            await message.answer(get_text('ADMIN_PROMO_CREATED'),
                                reply_markup=await promocodes_kb(session))
        else:
            raise Exception
    except Exception:
        await message.answer(get_text('ADMIN_PROMO_CREATE_ERROR'),
                                    reply_markup=back_button(path='promocodes'))


@admin_router.callback_query(F.data.startswith('promo_info='))
async def promo_info_pressed(callback: CallbackQuery, session: AsyncSession):
    id = int(callback.data.split('=')[1])

    data = (await PromocodesRepository.get_promo_with_id(id, session))['data']

    reusable = "Да" if data.reusable else "Нет"
    status = "🟢" if data.is_active else "🔴"

    await callback.message.edit_text(get_text('ADMIN_PROMO_INFO', promo=data.promo,
                                            quantity=data.quantity, percentage=data.percentage,
                                            reusable=reusable, status=status),
                                            reply_markup=promo_info_kb(id))



@admin_router.callback_query(F.data.startswith('del_promo='))
async def del_promo_pressed(callback: CallbackQuery, session: AsyncSession):
    id = int(callback.data.split('=')[1])

    success = (await PromocodesRepository.delete_promo(id, session))['success']

    try:
        if success:
            await callback.message.edit_text(get_text('ADMIN_PROMO_DELETED'),
                                            reply_markup=await promocodes_kb(session))
        else:
            raise Exception
    except Exception:
        await callback.message.edit_text(get_text('ADMIN_PROMO_DELETE_ERROR'),
                                                            reply_markup=await promocodes_kb(session))


# ----------------------------------------------------------


@admin_router.callback_query(F.data == 'user_panel_button')
async def user_panel_button_pressed(callback: CallbackQuery):
    await callback.message.edit_text(get_text('ADMIN_SWITCH_TO_USER_PANEL'),
                                        reply_markup=start_kb())


# -------------------- USERS -------------------------------


@admin_router.callback_query(F.data == 'users_button')
async def users_button_pressed(callback: CallbackQuery, session: AsyncSession):
    page = 1
    await callback.message.edit_text(get_text('ADMIN_USERS_LIST', page=page),
                                        reply_markup=await users_kb(page, session))


@admin_router.callback_query(F.data.startswith('users_page='))
async def users_page_selected(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split('=')[1])

    await callback.message.edit_text(get_text('ADMIN_USERS_LIST', page=page),
                                        reply_markup=await users_kb(page, session))


@admin_router.callback_query(F.data.startswith('user_info='))
async def user_info_pressed(callback: CallbackQuery, session: AsyncSession):
    tg_id = int(callback.data.split('=')[1])

    user = (await UsersRepository.get_user_with_tg_id(tg_id, session))['data']

    spent = (await PaymentsRepository.get_user_spent(tg_id, session))['data']

    status = "🟢" if user.is_active else "🔴"

    blocked = "✅" if user.is_blocked else "❌"

    await callback.message.edit_text(get_text('ADMIN_USER_INFO', name=user.name,
                                                tg_id=user.tg_id, username=user.username,
                                                referrer=user.from_tg_id, refs=user.refs,
                                                active_status=status, blocked_status=blocked,
                                                spent=spent),
                                                reply_markup=user_profile_kb(tg_id))



@admin_router.callback_query(F.data.startswith('ban_user='))
async def ban_user_pressed(callback: CallbackQuery, session: AsyncSession):
    tg_id = int(callback.data.split('=')[1])

    await UsersRepository.ban_or_unban_user(tg_id, session)

    user = (await UsersRepository.get_user_with_tg_id(tg_id, session))['data']

    if user.is_blocked:
        await callback.bot.send_message(tg_id, get_text('ADMIN_USER_BANNED', admin_username=ADMIN_USERNAME))
    else:
        await callback.bot.send_message(tg_id, get_text('ADMIN_USER_UNBANNED'), reply_markup=start_kb())

    spent = (await PaymentsRepository.get_user_spent(tg_id, session))['data']

    status = "🟢" if user.is_active else "🔴"
    
    blocked = "✅" if user.is_blocked else "❌"
    
    await callback.message.edit_text(get_text('ADMIN_USER_INFO', name=user.name,
                                                    tg_id=user.tg_id, username=user.username,
                                                    referrer=user.from_tg_id, refs=user.refs,
                                                    active_status=status, blocked_status=blocked,
                                                    spent=spent),
                                                    reply_markup=user_profile_kb(tg_id))


# -------------------- MAILING -----------------------------


@admin_router.callback_query(F.data == 'start_mailing_button')
async def start_mailing(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.mailing)

    await callback.message.answer(get_text('ADMIN_MAILING_INSTRUCTION'),
                                    reply_markup=back_button(text='Отмена'))


@admin_router.message(StateFilter(States.mailing))
async def mailing_process(message: Message, state: FSMContext, session: AsyncSession):
    user_ids = (await UsersRepository.get_all_users_tg_ids(session))['data']
    user_ids.remove(ADMIN_ID)

    for id in user_ids:
        try:
            await message.bot.copy_message(id, message.from_user.id, message.message_id)
        except TelegramForbiddenError:
            continue

    await message.answer(get_text('ADMIN_MAILING_SUCCESS'), reply_markup=admin_start_kb())

    await state.clear()


# ---------------- COMMANDS --------------------------


@admin_router.message(F.text == '/list')
async def get_list_of_commands(message: Message):
        await message.answer(get_text('ADMIN_COMMANDS_LIST'),
                            reply_markup=back_button())


@admin_router.message(F.text == '/get_db')
async def get_db_entered(message: Message):
        file = FSInputFile('core/database.db')
        await message.bot.send_document(message.from_user.id, file)


@admin_router.message(F.text.startswith('/get_user'))
async def get_user_command(message: Message, session: AsyncSession):
        user_id = int(message.text.split(' ')[1])

        user = (await UsersRepository.get_user_with_tg_id(user_id, session))['data']

        spent = (await PaymentsRepository.get_user_spent(user_id, session))['data']
        
        status = "🟢" if user.is_active else "🔴"
            
        blocked = "✅" if user.is_blocked else "❌"
            
        await message.answer(get_text('ADMIN_USER_INFO', name=user.name,
                                                        tg_id=user.tg_id, username=user.username,
                                                        referrer=user.from_tg_id, refs=user.refs,
                                                        active_status=status, blocked_status=blocked,
                                                        spent=spent),
                                                        reply_markup=user_profile_kb(user_id))


@admin_router.message(F.text.startswith('/create_key'))
async def create_key(message: Message, session: AsyncSession):
        expiry, traffic, devices = message.text.split(' ')[1:]

        expiry, exp_type = expiry.split('_')
        key = await create_user_vless_key(  message.from_user.id, session,
                                            'free', int(expiry), int(traffic), int(devices), 
                                            expiry_type=exp_type, bypass=True)
        await message.answer(f'{key}',
                            reply_markup=admin_start_kb())



@admin_router.message(F.text == '/test')
async def test(message: Message, session: AsyncSession):
    pass
    

