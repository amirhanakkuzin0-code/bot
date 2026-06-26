import asyncio
import logging
from dataclasses import dataclass
from typing import List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────────────────────
# КОНФИГ — замените на свои значения
# ─────────────────────────────────────────────────────────────

BOT_TOKEN: str = "8901168863:AAEGaG8XN6MSIMqjXBrGWIj_MbU-86ohfO4"
ADMIN_CHAT_ID: int = -1004393597676

# ─────────────────────────────────────────────────────────────
# МЕНЮ
# ─────────────────────────────────────────────────────────────

@dataclass
class MenuItem:
    id: str
    name: str
    description: str
    price: int
    photo_url: str

MENU: List[MenuItem] = [
    MenuItem(
        id="borsch",
        name="Борщ домашний",
        description="Наваристый борщ с говядиной, свёклой и сметаной. Подаётся с хлебом.",
        price=1200,
        photo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Borscht_served_in_Dnipropetrovsk.jpg/800px-Borscht_served_in_Dnipropetrovsk.jpg",
    ),
    MenuItem(
        id="puree_kotleta",
        name="Пюре с котлетой",
        description="Нежное картофельное пюре со сливочным маслом и сочной домашней котлетой.",
        price=1800,
        photo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Good_Food_Display_-_NCI_Visuals_Online.jpg/800px-Good_Food_Display_-_NCI_Visuals_Online.jpg",
    ),
    MenuItem(
        id="caesar",
        name="Салат Цезарь",
        description="Классический Цезарь с куриным филе, сухариками, пармезаном и фирменным соусом.",
        price=1500,
        photo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/800px-A_small_cup_of_coffee.JPG",
    ),
]

MENU_BY_ID: dict = {item.id: item for item in MENU}

# ─────────────────────────────────────────────────────────────
# FSM СОСТОЯНИЯ
# ─────────────────────────────────────────────────────────────

class OrderForm(StatesGroup):
    waiting_name    = State()
    waiting_phone   = State()
    waiting_address = State()

# ─────────────────────────────────────────────────────────────
# КЛАВИАТУРЫ
# ─────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Посмотреть меню 🍲",   callback_data="show_menu"))
    builder.row(InlineKeyboardButton(text="Моя корзина 🛒",       callback_data="show_cart"))
    builder.row(InlineKeyboardButton(text="О нас & Контакты ℹ️", callback_data="about"))
    return builder.as_markup()

def item_kb(item_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить в корзину 🛒", callback_data=f"add:{item_id}")
    return builder.as_markup()

def cart_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Очистить корзину ❌", callback_data="clear_cart"),
        InlineKeyboardButton(text="Оформить заказ ✅",  callback_data="checkout"),
    )
    return builder.as_markup()

def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

# ─────────────────────────────────────────────────────────────
# ХЕЛПЕРЫ КОРЗИНЫ
# ─────────────────────────────────────────────────────────────

async def get_cart(state: FSMContext) -> dict:
    data = await state.get_data()
    return data.get("cart", {})

async def set_cart(state: FSMContext, cart: dict):
    await state.update_data(cart=cart)

def cart_text(cart: dict) -> tuple[str, int]:
    lines = []
    total = 0
    for idx, (item_id, qty) in enumerate(cart.items(), 1):
        item = MENU_BY_ID[item_id]
        subtotal = item.price * qty
        total += subtotal
        lines.append(f"{idx}. {item.name} × {qty} — {subtotal:,} ₸".replace(",", " "))
    text = "🛒 <b>Ваш заказ:</b>\n\n" + "\n".join(lines) + f"\n\n<b>Итого: {total:,} ₸</b>".replace(",", " ")
    return text, total

# ─────────────────────────────────────────────────────────────
# ХЭНДЛЕРЫ
# ─────────────────────────────────────────────────────────────

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в <b>FoodВайб</b>!\n\n"
        "Горячие обеды прямо в ваш офис 🏢\n"
        "Выберите, что хотите сделать:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

@router.callback_query(F.data == "show_menu")
async def show_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🍽 <b>Наше меню:</b>", parse_mode="HTML")
    for item in MENU:
        caption = (
            f"<b>{item.name}</b>\n"
            f"{item.description}\n\n"
            f"💰 <b>{item.price:,} ₸</b>".replace(",", " ")
        )
        try:
            await callback.message.answer_photo(
                photo=item.photo_url,
                caption=caption,
                reply_markup=item_kb(item.id),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.answer(caption, reply_markup=item_kb(item.id), parse_mode="HTML")

@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split(":")[1]
    cart = await get_cart(state)
    cart[item_id] = cart.get(item_id, 0) + 1
    await set_cart(state, cart)
    name = MENU_BY_ID[item_id].name if item_id in MENU_BY_ID else item_id
    await callback.answer(f"✅ «{name}» добавлен в корзину!", show_alert=True)

@router.callback_query(F.data == "show_cart")
async def show_cart(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    cart = await get_cart(state)
    if not cart:
        await callback.message.answer(
            "🛒 Ваша корзина пуста.\nСамое время что-нибудь выбрать! 😊",
            reply_markup=main_menu_kb(),
        )
        return
    text, _ = cart_text(cart)
    await callback.message.answer(text, reply_markup=cart_kb(), parse_mode="HTML")

@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await set_cart(state, {})
    await callback.answer("Корзина очищена ✅", show_alert=True)
    await callback.message.edit_text("🛒 Корзина пуста.\nВозвращайтесь за вкусным! 😊")

@router.callback_query(F.data == "checkout")
async def checkout_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not await get_cart(state):
        await callback.message.answer("Корзина пуста! Добавьте что-нибудь 😊")
        return
    await state.set_state(OrderForm.waiting_name)
    await callback.message.answer(
        "📝 Оформляем заказ!\n\n<b>Шаг 1 из 3.</b> Введите ваше имя:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

@router.message(OrderForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(customer_name=message.text.strip())
    await state.set_state(OrderForm.waiting_phone)
    await message.answer(
        "<b>Шаг 2 из 3.</b> Укажите ваш номер телефона\n"
        "Можно нажать кнопку ниже или написать вручную:",
        reply_markup=share_phone_kb(),
        parse_mode="HTML",
    )

@router.message(OrderForm.waiting_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    await _ask_address(message, state, message.contact.phone_number)

@router.message(OrderForm.waiting_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    await _ask_address(message, state, message.text.strip())

async def _ask_address(message: Message, state: FSMContext, phone: str):
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.waiting_address)
    await message.answer(
        "<b>Шаг 3 из 3.</b> Введите адрес доставки\n"
        "<i>Пример: ул. Пушкина, дом 10, офис 302</i>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

@router.message(OrderForm.waiting_address)
async def process_address(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cart = data.get("cart", {})
    customer_name = data.get("customer_name", "—")
    phone = data.get("phone", "—")
    address = message.text.strip()
    _, total = cart_text(cart)

    await message.answer(
        "🎉 <b>Спасибо!</b> Ваш заказ принят.\n"
        "Менеджер свяжется с вами для подтверждения. 📞",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

    order_lines = "\n".join(
        f"  • {MENU_BY_ID[iid].name} ({qty} шт.)" for iid, qty in cart.items() if iid in MENU_BY_ID
    )
    admin_text = (
        "🚨 <b>НОВЫЙ ЗАКАЗ!</b> 🚨\n\n"
        f"👤 <b>Клиент:</b> {customer_name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"📍 <b>Адрес:</b> {address}\n\n"
        f"🛒 <b>Заказ:</b>\n{order_lines}\n\n"
        f"💵 <b>Сумма к оплате: {total:,} ₸</b>".replace(",", " ")
    )
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление в админ-чат: {e}")

    await state.clear()

@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "ℹ️ <b>FoodВайб</b> — доставка горячих обедов в офисы.\n\n"
        "📞 Телефон: <b>+7 700 000 00 00</b>\n"
        "📱 WhatsApp: <b>+7 700 000 00 00</b>\n"
        "🕐 Режим работы: <b>Пн–Пт, 9:00–18:00</b>\n\n"
        "С удовольствием ответим на ваши вопросы! 😊",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

# ─────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
