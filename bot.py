import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile

# ---------- Настройки ----------
API_TOKEN = "8992254572:AAEf_3z5Tu1oXoEH8JTJdWxZIfuYiNdsmDg"          # замените на реальный токен
ADMIN_ID = 1467435264                 # ваш Telegram ID
USERS_FILE = "users.json"            # файл с ID пользователей

# ---------- Инициализация ----------
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ---------- Состояния для рассылки ----------
class BroadcastState(StatesGroup):
    waiting_for_content = State()   # бот ждёт сообщение для рассылки

# ---------- Вспомогательные функции для users.json ----------
def load_users() -> set:
    """Загружает множество user_id из файла."""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data)
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_users(users: set):
    """Сохраняет множество user_id в файл."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(users)), f, ensure_ascii=False, indent=2)

# ---------- Обработчик /start ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветствие и сохранение пользователя."""
    user_id = message.from_user.id
    users = load_users()

    if user_id not in users:
        users.add(user_id)
        save_users(users)
        logging.info(f"Добавлен новый пользователь: {user_id}")

    # Здесь ваш существующий код приветствия (не меняем)
    await message.answer(
        "Привет! Я бот-калькулятор. Введите /help для списка команд."
    )

# ---------- Команда /broadcast (только для администратора) ----------
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Активирует режим рассылки (только для ADMIN_ID)."""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав на эту команду.")
        return

    await state.set_state(BroadcastState.waiting_for_content)
    await message.answer(
        "📢 Отправьте сообщение (текст, фото, видео, документ или анимацию), "
        "которое нужно разослать всем пользователям."
    )

# ---------- Приём контента для рассылки (в состоянии ожидания) ----------
@dp.message(StateFilter(BroadcastState.waiting_for_content))
async def process_broadcast_content(message: Message, state: FSMContext):
    """Отправляет полученный контент всем пользователям из users.json."""
    users = load_users()
    if not users:
        await message.answer("❌ Список пользователей пуст. Рассылка отменена.")
        await state.clear()
        return

    success = 0
    errors = 0

    # Определяем тип контента
    content_type = None
    if message.photo:
        content_type = "photo"
    elif message.video:
        content_type = "video"
    elif message.document:
        content_type = "document"
    elif message.animation:
        content_type = "animation"
    else:
        content_type = "text"

    await message.answer(f"⏳ Начинаю рассылку ({len(users)} получателей)...")

    for user_id in users:
        try:
            if content_type == "photo":
                # Берём фото наилучшего качества
                await bot.send_photo(
                    user_id,
                    message.photo[-1].file_id,
                    caption=message.caption or "",
                    caption_entities=message.caption_entities
                )
            elif content_type == "video":
                await bot.send_video(
                    user_id,
                    message.video.file_id,
                    caption=message.caption or "",
                    caption_entities=message.caption_entities
                )
            elif content_type == "document":
                await bot.send_document(
                    user_id,
                    message.document.file_id,
                    caption=message.caption or "",
                    caption_entities=message.caption_entities
                )
            elif content_type == "animation":
                await bot.send_animation(
                    user_id,
                    message.animation.file_id,
                    caption=message.caption or "",
                    caption_entities=message.caption_entities
                )
            else:  # text
                await bot.send_message(
                    user_id,
                    message.text,
                    entities=message.entities
                )
            success += 1
            await asyncio.sleep(0.05)  # небольшая задержка, чтобы не упереться в лимиты

        except Exception as e:
            logging.warning(f"Ошибка отправки пользователю {user_id}: {e}")
            errors += 1
            # Если бот заблокирован — удаляем ID, чтобы не спамить в будущем
            if "bot was blocked by the user" in str(e).lower():
                users.discard(user_id)
                save_users(users)

    # Финальный отчёт
    await state.clear()
    await message.answer(
        "✅ Рассылка завершена.\n"
        f"Отправлено: {success}\n"
        f"Ошибок: {errors}"
    )

# ---------- Пример существующего функционала (не изменяем) ----------
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Список команд: /start, /help, /broadcast (админ)")

# ---------- Запуск ----------
async def main():
    # При необходимости создаём файл users.json, если его нет
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            pass
    except FileNotFoundError:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
