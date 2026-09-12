import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, 
    FSInputFile, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from aiogram.filters import CommandStart
import yt_dlp

# Безопасное получение токена
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временное хранилище результатов поиска (user_id -> данные)
user_searches = {}

# Главное меню (Reply Keyboard)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Поиск музыки"), KeyboardButton(text="🔥 Популярное")],
        [KeyboardButton(text="📞 Поддержка & Контакты"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

# Inline-клавиатура контактов
contacts_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Разработчик в TG", url="https://t.me/your_username")],
        [InlineKeyboardButton(text="💬 WhatsApp Поддержка", url="https://wa.me/79000000000")],
        [InlineKeyboardButton(text="👥 Чат отзывов и идей", url="https://t.me/your_chat_link")]
    ]
)

@dp.message(CommandStart())
async def start_cmd(message: Message):
    welcome_text = (
        "✨ Добро пожаловать в элитный музыкальный бот!\n\n"
        "🎧 Здесь ты можешь найти и скачать абсолютно любой трек в высоком качестве.\n\n"
        "👇 Просто отправь мне название песни или имя исполнителя!"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Помощь")
async def help_cmd(message: Message):
    help_text = (
        "📌 Как пользоваться ботом:\n\n"
        "1️⃣ Напиши название песни в чат (например: Miyagi - Utopia).\n"
        "2️⃣ Бот пришлет удобный список результатов.\n"
        "3️⃣ Нажми на цифру с нужным треком для скачивания.\n"
        "4️⃣ Используй стрелочки ◀️ ▶️ для переключения страниц!"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.text == "🔥 Популярное")
async def top_cmd(message: Message):
    await message.answer("🔥 Популярные запросы сегодня:\n1. Miyagi\n2. Xcho\n3. Macan\n4. INSTASAMKA\n\nОтправь имя любого из них для поиска!")

@dp.message(F.text == "📞 Поддержка & Контакты")
async def contacts_cmd(message: Message):
    await message.answer(
        "🤝 Связь с нами и поддержка:\nВыберите нужный раздел ниже:",
        reply_markup=contacts_inline
    )

def build_search_keyboard(tracks, page=0, per_page=5):
    """Генерация клавиатуры с кнопками скачивания и пагинацией"""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_tracks = tracks[start_idx:end_idx]

    buttons = []
    
    # Кнопки выбора трека (1-5 на страницу)
    track_buttons = []
    for i in range(len(current_tracks)):
        real_num = start_idx + i + 1
        track_buttons.append(InlineKeyboardButton(text=f"🎵 {real_num}", callback_data=f"dl_{start_idx + i}"))
    buttons.append(track_buttons)

    # Кнопки навигации (Назад / Вперед)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{page - 1}"))
    if end_idx < len(tracks):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page_{page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_search_text(query, tracks, page=0, per_page=5):
    """Форматирование списка треков"""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_tracks = tracks[start_idx:end_idx]

    text = f"🔍 Результаты поиска по запросу: {query}\n"
    text += f"📄 *Страница {page + 1} из {(len(tracks) - 1) // per_page + 1}*\n\n"

    for i, track in enumerate(current_tracks, start=start_idx + 1):
        text += f"{i}. {track['title']} [{track['duration']}]\n"

    text += "\n👇 *Нажмите на кнопку с номером трека для скачивания:*"
    return text
    @dp.message(F.text)
async def search_handler(message: Message):
    if message.text.startswith("/"):
        return

    query = message.text
    status_msg = await message.answer(f"🔍 *Ищу {query}...*", parse_mode="Markdown")

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch15', # Ищем до 15 вариантов
        'noplaylist': True,
    }

    loop = asyncio.get_running_loop()

    def search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)

    try:
        info = await loop.run_in_executor(None, search)
        entries = info.get('entries', [])

        if not entries:
            await status_msg.edit_text("❌ Ничего не найдено. Попробуйте изменить запрос.")
            return

        tracks = []
        for entry in entries:
            duration = entry.get('duration', 0)
            mins, secs = divmod(duration, 60)
            dur_str = f"{mins}:{secs:02d}" if duration else "--:--"

            tracks.append({
                'title': entry.get('title', 'Без названия'),
                'url': entry.get('webpage_url'),
                'duration': dur_str
            })

        user_searches[message.from_user.id] = {
            'query': query,
            'tracks': tracks
        }

        text = format_search_text(query, tracks, page=0)
        kb = build_search_keyboard(tracks, page=0)

        await status_msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text("❌ Ошибка при поиске.")
        print(f"Ошибка поиска: {e}")

@dp.callback_query(F.data.startswith("page_"))
async def page_callback(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    user_data = user_searches.get(callback.from_user.id)

    if not user_data:
        await callback.answer("Сессия поиска истекла. Введите запрос заново.", show_alert=True)
        return

    text = format_search_text(user_data['query'], user_data['tracks'], page=page)
    kb = build_search_keyboard(user_data['tracks'], page=page)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(callback: CallbackQuery):
    track_idx = int(callback.data.split("_")[1])
    user_data = user_searches.get(callback.from_user.id)

    if not user_data or track_idx >= len(user_data['tracks']):
        await callback.answer("Ошибка доступа. Введите запрос заново.", show_alert=True)
        return

    track = user_data['tracks'][track_idx]
    await callback.answer(f"Загрузка: {track['title']}")
    status = await callback.message.answer(f"⬇️ *Скачиваю:* {track['title']}...", parse_mode="Markdown")

    unique_id = str(uuid.uuid4())
    out_template = f"downloads/{unique_id}.%(ext)s"
    expected_filename = f"downloads/{unique_id}.mp3"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    loop = asyncio.get_running_loop()

    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([track['url']])

    try:
        await loop.run_in_executor(None, download)

        if os.path.exists(expected_filename):
            await status.edit_text("📤 *Отправка файла...*", parse_mode="Markdown")
            audio = FSInputFile(expected_filename)
            await callback.message.answer_audio(
                audio=audio, 
                title=track['title'],
                caption="🎧 *Cкачано с помощью вашего бота*"
                )
            await status.delete()
            os.remove(expected_filename)
        else:
            await status.edit_text("❌ Ошибка обработки аудиофайла.")
    except Exception as e:
        await status.edit_text("❌ Ошибка при скачивании.")
        print(f"Ошибка загрузки: {e}")

async def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    await dp.start_polling(bot)

if name == 'main':
    asyncio.run(main())
