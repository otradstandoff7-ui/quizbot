import json
import random
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import init_db, update_stats, get_top, get_profile

TOKEN = "8515246761:AAFNbQWnN9kwSU5kup0z0R2WrpKT7B4xVAQ"

bot = Bot(TOKEN)
dp = Dispatcher()

TIME_LIMIT = 30  # секунд

# ---------- ЗАГРУЗКА СТРАН ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, "data.json")

with open(data_path, "r", encoding="utf-8") as f:
    countries = json.load(f)

active_questions = {}
active_timers = {}

# ---------- КЛАВИАТУРА ----------
def modes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏳 Флаг → Страна", callback_data="flag_country")],
        [InlineKeyboardButton(text="🌍 Страна → Флаг", callback_data="country_flag")],
        [InlineKeyboardButton(text="🏙 Страна → Столица", callback_data="country_capital")],
        [InlineKeyboardButton(text="📍 Столица → Страна", callback_data="capital_country")]
    ])

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Выбери режим:", reply_markup=modes_keyboard())

@dp.message(Command("menu"))
async def menu_cmd(message: Message):
    await message.answer("Выбери режим:", reply_markup=modes_keyboard())

# ---------- ГЕНЕРАЦИЯ ВОПРОСА ----------
def generate_question(mode):
    correct = random.choice(countries)
    options = [correct]

    while len(options) < 4:
        r = random.choice(countries)
        if r not in options:
            options.append(r)

    random.shuffle(options)

    if mode == "flag_country":
        question = correct["flag"]
        answers = [o["name"] for o in options]
        correct_answer = correct["name"]

    elif mode == "country_flag":
        question = correct["name"]
        answers = [o["flag"] for o in options]
        correct_answer = correct["flag"]

    elif mode == "country_capital":
        question = correct["name"]
        answers = [o["capital"] for o in options]
        correct_answer = correct["capital"]

    else:
        question = correct["capital"]
        answers = [o["name"] for o in options]
        correct_answer = correct["name"]

    return question, answers, correct_answer

# ---------- ОТПРАВКА ВОПРОСА ----------
async def send_question(message, user_id, mode):
    if user_id in active_timers:
        active_timers[user_id].cancel()

    question, answers, correct = generate_question(mode)
    active_questions[user_id] = (mode, correct)

    if mode == "flag_country":
        buttons = [[InlineKeyboardButton(text=a, callback_data=f"ans|{a}")] for a in answers]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer_photo(question, caption="Какая страна?", reply_markup=kb)

    elif mode == "country_flag":
        await message.answer(f"Выбери флаг для: {question}")
        for a in answers:
            await message.answer_photo(
                a,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Выбрать", callback_data=f"ans|{a}")]
                    ]
                )
            )

    else:
        buttons = [[InlineKeyboardButton(text=a, callback_data=f"ans|{a}")] for a in answers]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        if mode == "country_capital":
            await message.answer(f"Столица страны {question}?", reply_markup=kb)
        else:
            await message.answer(f"Какая страна имеет столицу {question}?", reply_markup=kb)

    task = asyncio.create_task(timeout_user(user_id))
    active_timers[user_id] = task

async def send_question_by_id(user_id, mode):
    chat = await bot.get_chat(user_id)
    await send_question(chat, user_id, mode)

# ---------- ТАЙМЕР ----------
async def timeout_user(user_id):
    try:
        await asyncio.sleep(TIME_LIMIT)

        if user_id in active_questions:
            mode, correct_answer = active_questions.pop(user_id)

            await bot.send_message(
                user_id,
                f"⏳ Время вышло!\nПравильный ответ: {correct_answer}"
            )

            await asyncio.sleep(1)
            await send_question_by_id(user_id, mode)

    except asyncio.CancelledError:
        return

# ---------- ЗАПУСК РЕЖИМА ----------
@dp.callback_query(F.data.in_(
    ["flag_country", "country_flag", "country_capital", "capital_country"]
))
async def start_quiz(call: CallbackQuery):
    await send_question(call.message, call.from_user.id, call.data)

# ---------- ОТВЕТ ----------
@dp.callback_query(F.data.startswith("ans"))
async def answer_handler(call: CallbackQuery):
    user_id = call.from_user.id

    if user_id not in active_questions:
        await call.answer("Время вышло", show_alert=True)
        return

    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]

    mode, correct_answer = active_questions.pop(user_id)
    user_answer = call.data.split("|")[1]

    correct = user_answer == correct_answer

    await update_stats(
        user_id,
        call.from_user.username or call.from_user.full_name,
        mode,
        correct
    )

    if correct:
        await call.message.answer("✅ Верно")
    else:
        await call.message.answer(f"❌ Неверно\nПравильный ответ: {correct_answer}")

    await asyncio.sleep(1)
    await send_question(call.message, user_id, mode)

# ---------- ПРОФИЛЬ ----------
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    data = await get_profile(message.from_user.id)

    if not data:
        await message.answer("Ты ещё не играл.")
        return

    fc_c, fc_t, cf_c, cf_t, cc_c, cc_t, cap_c, cap_t = data

    total_correct = fc_c + cf_c + cc_c + cap_c
    total_total = fc_t + cf_t + cc_t + cap_t

    percent = round((total_correct / total_total) * 100, 2) if total_total > 0 else 0

    text = f"""
👤 Твой профиль

🏳 Флаг → Страна: {fc_c}/{fc_t}
🌍 Страна → Флаг: {cf_c}/{cf_t}
🏙 Страна → Столица: {cc_c}/{cc_t}
📍 Столица → Страна: {cap_c}/{cap_t}

🔥 Всего: {total_correct}/{total_total}
🎯 Точность: {percent}%
"""
    await message.answer(text)

# ---------- ТОП ----------
@dp.message(Command("top"))
async def top_handler(message: Message):
    args = message.text.split()

    if len(args) == 1:
        top = await get_top()
        text = "🌍 Глобальный ТОП\n\n"
        for i, u in enumerate(top, 1):
            text += f"{i}. {u[0]} — {u[1]}\n"
        await message.answer(text)
        return

    mode = args[1]
    top = await get_top(mode)

    text = "🏆 ТОП 20\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u[0]}\n"
        text += f"   ✔ {u[1]}/{u[2]} ({u[3]}%)\n\n"

    await message.answer(text)

# ---------- HELP ----------
@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer("""
📌 Команды:
/start — запуск
/menu — выбор режима
/stop — остановить игру
/profile — статистика
/top — глобальный рейтинг
/help — помощь
""")

# ---------- STOP ----------
@dp.message(Command("stop"))
async def stop_cmd(message: Message):
    user_id = message.from_user.id

    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]

    if user_id in active_questions:
        del active_questions[user_id]

    await message.answer("⛔ Игра остановлена.\n/menu — начать заново.")

# ---------- MAIN ----------
async def main():
    print("Бот запускается...")
    await init_db()
    print("База инициализирована")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())