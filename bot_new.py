# ===============================
# Импорт стандартных модулей
# ===============================
import logging
import asyncio
from datetime import datetime

# ===============================
# Импорт библиотек для бота и HTTP-запросов
# ===============================
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import aiohttp
import pandas as pd

# ===============================
# Настройка логирования
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ===============================
# Конфигурация бота
# ===============================
BOT_TOKEN = "7881397083:AAHOs_B0cDLYFUWYU67udqSJ6LF8PCphneA"
MESS_MAX_LENGTH = 4096

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# Загрузка данных из Excel
# ===============================
try:
    df = pd.read_excel("file.xlsx")
    df1 = pd.read_excel("plan.xlsx")
    df1["day"] = df1["day"].dt.strftime("%Y-%m-%d")
    book_names = df["Книга Библии"].tolist()
    book_values = df["book"].tolist()
    book_dict = dict(zip(book_values, book_names))
except FileNotFoundError:
    logging.error("Ошибка: файлы не найдены.")
    exit()
except KeyError as e:
    logging.error("Ошибка в структуре Excel: {}".format(e))
    exit()

# Словарь соответствия сокращений книг
book_dict2 = {
    "Быт": 1, "Исх": 2, "Лев": 3, "Чис": 4, "Втор": 5, "Нав": 6, "Суд": 7, "Руф": 8,
    "1Цар": 9, "2Цар": 10, "3Цар": 11, "4Цар": 12, "1Пар": 13, "2Пар": 14, "Езд": 15,
    "Неем": 16, "Есф": 17, "Иов": 18, "Пс": 19, "Прит": 20, "Еккл": 21, "Песн": 22,
    "Ис": 23, "Иер": 24, "Плач": 25, "Иез": 26, "Дан": 27, "Ос": 28, "Иоил": 29,
    "Ам": 30, "Авд": 31, "Ион": 32, "Мих": 33, "Наум": 34, "Авв": 35, "Соф": 36,
    "Агг": 37, "Зах": 38, "Мал": 39, "Мф": 40, "Мк": 41, "Лк": 42, "Ин": 43,
    "Деян": 44, "Рим": 45, "1Кор": 46, "2Кор": 47, "Гал": 48, "Еф": 49, "Флп": 50,
    "Кол": 51, "1Фес": 52, "2Фес": 53, "1Тим": 54, "2Тим": 55, "Тит": 56, "Флм": 57,
    "Евр": 58, "Иак": 59, "1Пет": 60, "2Пет": 61, "1Ин": 62, "2Ин": 63, "3Ин": 64,
    "Иуд": 65, "Откр": 66
}

# ===============================
# Глобальные состояния пользователей
# ===============================
user_page = {}
user_chosen_book = {}
user_current_chapter = {}

# ===============================
# API-функции
# ===============================


async def get_chapter_gospel(book, chapter):
    url = "https://justbible.ru/api/bible?translation=rst&book={}&chapter={}".format(book, chapter)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
    except Exception as e:
        logging.error("API Error: {}".format(e))
        return "Ошибка: {}".format(e)

    verses = [v for k, v in data.items() if k != "info"]
    testament = "Ветхий завет" if book < 40 else "Новый завет"
    text = "{}. {}:\n{}".format(testament, data['info']['book'], chapter, ' '.join(verses))

    return text  # Вернем полный текст для разбиения позже


async def get_random_verse_rbo():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://justbible.ru/api/random?translation=rbo", timeout=10) as response:
                data = await response.json()
        return "{} - {}".format(data['info'], data['verse'])
    except Exception as e:
        logging.error("Random verse error: {}".format(e))
        return "Не удалось получить стих"


# ===============================
# Вспомогательная функция для разбивки длинных сообщений
# ===============================
def split_text(text, max_length=MESS_MAX_LENGTH):
    """
    Разбивает длинный текст на части, не превышающие максимальную длину.
    Старается сохранить целостность абзацев.
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    while len(text) > 0:
        # Ищем последний перенос строки в допустимом диапазоне
        split_position = text.rfind('\n', 0, max_length)

        # Если не нашли перенос - ищем последний пробел
        if split_position == -1:
            split_position = text.rfind(' ', 0, max_length)

        # Если совсем не нашли подходящего места - форсированно обрезаем
        if split_position == -1:
            split_position = max_length

        part = text[:split_position].strip()
        if part:
            parts.append(part)
        text = text[split_position:].strip()

    return parts
# ===============================
# Функции клавиатур (ИСПРАВЛЕННЫЕ)
# ===============================


def create_book_keyboard(chat_id, page=0, per_page=10):
    buttons = []
    start = page * per_page
    end = start + per_page

    # Добавляем кнопки книг
    for i in range(start, min(end, len(book_names))):
        buttons.append([
            InlineKeyboardButton(
                text=book_names[i],
                callback_data="select_book_{}".format(book_values[i])
            )
        ])

    # Добавляем навигацию
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="nav_page_{}".format(page-1)
            )
        )
    if end < len(book_names):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data="nav_page_{}".format(page+1)
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_next_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Следующая глава",
                callback_data="next_chapter"
            )
        ]]
    )


def create_reading_buttons(reading_str):
    buttons = []
    for part in reading_str.split(";"):
        part = part.strip()
        if not part:
            continue

        try:
            book_code, chapters = part.split(".")
            book_code = book_code.strip()
            chapters = chapters.strip()

            if book_code not in book_dict2:
                continue

            book_id = book_dict2[book_code]

            # Обработка диапазона глав
            if "-" in chapters:
                start, end = map(int, chapters.split("-"))
                for chapter in range(start, end+1):
                    buttons.append([
                        InlineKeyboardButton(
                            text="{} {}".format(book_code, chapter),
                            callback_data="daily_{}_{}".format(book_id, chapter)
                        )
                    ])
            else:
                buttons.append([
                    InlineKeyboardButton(
                        text="{} {}".format(book_code, chapters),
                        callback_data="daily_{}_{}".format(book_id, chapters)
                    )
                ])
        except Exception as e:
            logging.error("Error parsing reading: {}".format(e))

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===============================
# Обработчики сообщений
# ===============================


@dp.message(Command("start"))
async def start(message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выбрать книгу, главу")],
            [KeyboardButton(text="Случайные главы")],
            [KeyboardButton(text="Что читать сегодня")]
        ],
        resize_keyboard=True
    )
    await message.answer("Добро пожаловать!", reply_markup=kb)


@dp.message(F.text == "Выбрать книгу, главу")
async def book_selection(message):
    user_page[message.chat.id] = 0
    await message.answer(
        "Выберите книгу:",
        reply_markup=create_book_keyboard(message.chat.id)
    )


@dp.message(F.text == "Случайные главы")
async def random_verse(message):
    text = await get_random_verse_rbo()
    await message.answer(text)


@dp.message(F.text == "Что читать сегодня")
async def daily_reading(message):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        plan = df1[df1["day"] == today].iloc[0]
        await message.answer(
            "Чтение на {}:".format(today),
            reply_markup=create_reading_buttons(plan["book_list"])
        )
    except IndexError:
        await message.answer("На сегодня чтений нет")

# ===============================
# Обработчики колбэков
# ===============================


@dp.callback_query(F.data.startswith("select_book_"))
async def book_selected(callback):
    book_id = int(callback.data.split("_")[2])
    user_chosen_book[callback.message.chat.id] = book_id
    await callback.message.answer("Введите номер главы:")


@dp.callback_query(F.data.startswith("nav_page_"))
async def page_navigation(callback):
    page = int(callback.data.split("_")[2])
    chat_id = callback.message.chat.id
    user_page[chat_id] = page
    await callback.message.edit_reply_markup(
        reply_markup=create_book_keyboard(chat_id, page)
    )


@dp.callback_query(F.data == "next_chapter")
async def next_chapter(callback):
    chat_id = callback.message.chat.id
    if chat_id not in user_chosen_book or chat_id not in user_current_chapter:
        return await callback.answer("Сначала выберите книгу и главу")

    book = user_chosen_book[chat_id]
    chapter = user_current_chapter[chat_id] + 1
    text = await get_chapter_gospel(book, chapter)

    user_current_chapter[chat_id] = chapter

    for part in split_text(text):  # Разбиваем перед отправкой
        await callback.message.answer(part)

    await callback.message.answer("Выберите действие:", reply_markup=create_next_button())


@dp.callback_query(F.data.startswith("daily_"))
async def daily_selected(callback):
    _, book_id, chapter = callback.data.split("_")
    text = await get_chapter_gospel(int(book_id), int(chapter))

    for part in split_text(text):  # Разбиваем перед отправкой
        await callback.message.answer(part)

    await callback.message.answer("Выберите действие:", reply_markup=create_next_button())


@dp.message(F.text.isdigit())
async def chapter_input(message):
    chat_id = message.chat.id
    if chat_id not in user_chosen_book:
        return

    try:
        chapter = int(message.text)
        book = user_chosen_book[chat_id]
        text = await get_chapter_gospel(book, chapter)
        user_current_chapter[chat_id] = chapter

        for part in split_text(text):  # Разбиваем перед отправкой
            await message.answer(part)

        await message.answer("Выберите действие:", reply_markup=create_next_button())
    except Exception as e:
        await message.answer("Ошибка: {}".format(e))


# ===============================
# Запуск бота
# ===============================


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
