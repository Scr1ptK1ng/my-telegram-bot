import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from random import choice

# 🔑 Токен
BOT_TOKEN = "8073634244:AAE_AZ8Ib14OkcLixU3ve0Mx0hXVACQBp7w"

# 📁 Путь к JSON-файлу
DATA_FILE = "user_data.json"

# 📂 Загрузка и сохранение данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

# 💾 База данных пользователей
user_data = load_data()

# 📸 Мотивационные сообщения
motivations = [
    "Ты на верном пути! 💪",
    "Продолжай копить — цель рядом! 💰",
    "Ты красавчик(а), не сдавайся! 🔥",
    "Один шаг ближе к мечте 📈"
]

# 🤖 Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Функция, возвращающая главное меню в виде inline клавиатуры
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить цель", callback_data="setgoal")],
        [InlineKeyboardButton(text="Добавить сумму", callback_data="add")],
        [InlineKeyboardButton(text="Снять деньги", callback_data="withdraw")],
        [InlineKeyboardButton(text="Показать прогресс", callback_data="progress")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])

# Inline-клавиатура для отмены ввода (кнопка "Назад")
cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад", callback_data="cancel_input")]
])

# 📂 Машина состояний
class Form(StatesGroup):
    goal = State()
    add_amount = State()
    withdraw = State()

# 💬 /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"goal": 0, "balance": 0}
        save_data()
    await message.answer(
        "👋 Привет! Я твой трекер накоплений.\n\nВыбери действие:",
        reply_markup=get_main_menu()
    )

# Единый обработчик inline-кнопок
async def main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "setgoal":
        await state.clear()
        await callback.message.edit_text("💡 Введи сумму твоей цели:", reply_markup=cancel_kb)
        await state.set_state(Form.goal)
    elif data == "add":
        await state.clear()
        await callback.message.edit_text("💰 Введи сумму, которую ты накопил:", reply_markup=cancel_kb)
        await state.set_state(Form.add_amount)
    elif data == "withdraw":
        await state.clear()
        await callback.message.edit_text("💸 Введи сумму, которую хочешь снять:", reply_markup=cancel_kb)
        await state.set_state(Form.withdraw)
    elif data == "progress":
        user_id = str(callback.from_user.id)
        goal = user_data[user_id].get("goal", 0)
        balance = user_data[user_id].get("balance", 0)
        if goal == 0:
            text = "⛔ Цель не установлена. Выбери 'Установить цель'."
        else:
            percent = round((balance / goal) * 100, 2)
            text = f"📊 Прогресс: {balance} / {goal} тг ({percent}%)"
        await callback.message.edit_text(text, reply_markup=get_main_menu())
    elif data in ("cancel", "cancel_input"):
        await state.clear()
        await callback.message.edit_text("Ввод отменён.", reply_markup=get_main_menu())
    else:
        await callback.answer("Неизвестная команда.")
        return
    await callback.answer()

# Регистрируем callback‑хэндлер после определения функции
dp.callback_query.register(main_menu_callback)

# Обработчик текстовых сообщений для установки цели
@dp.message(Form.goal)
async def process_goal_input(message: Message, state: FSMContext):
    try:
        goal_text = message.text.replace(",", ".").strip()
        goal = float(goal_text)
        if goal <= 0:
            await message.answer("❗ Введи положительное число.", reply_markup=cancel_kb)
            return
        user_id = str(message.from_user.id)
        user_data[user_id]["goal"] = goal
        save_data()
        await message.answer(f"🎯 Цель установлена: {goal} тг", reply_markup=get_main_menu())
        await send_motivation(message)
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введи число (например, 100000).", reply_markup=cancel_kb)

# Обработчик текстовых сообщений для добавления суммы
@dp.message(Form.add_amount)
async def process_add_input(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        user_id = str(message.from_user.id)
        user_data[user_id]["balance"] += amount
        save_data()
        await message.answer(f"💸 Добавлено: {amount} тг", reply_markup=get_main_menu())
        await send_motivation(message)
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи число!", reply_markup=cancel_kb)

# Обработчик текстовых сообщений для снятия средств
@dp.message(Form.withdraw)
async def process_withdraw_input(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        user_id = str(message.from_user.id)
        current_balance = user_data[user_id]["balance"]
        if amount <= 0:
            await message.answer("❗ Введи положительное число.", reply_markup=cancel_kb)
            return
        if amount > current_balance:
            await message.answer("❌ Недостаточно средств для снятия.", reply_markup=cancel_kb)
            return
        user_data[user_id]["balance"] = current_balance - amount
        save_data()
        await message.answer(
            f"💸 Снято: {amount} тг. Остаток: {user_data[user_id]['balance']} тг.",
            reply_markup=get_main_menu()
        )
        await send_motivation(message)
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введи число.", reply_markup=cancel_kb)

# 🔥 Мотивашка — отправка текстового мотивационного сообщения
async def send_motivation(message: Message):
    await message.answer(choice(motivations))

# 🚀 Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
