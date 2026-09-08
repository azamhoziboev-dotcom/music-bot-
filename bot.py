import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
import yt_dlp

BOT_TOKEN = '8649653758:AAGlxRShPYtuqdiAPxsjPeuVGtiqJMNFjT4'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Главное меню с кнопками
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="🎵 Как скачать?")],
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "Привет! Я бот для поиска и скачивания музыки.\n\n"
        "Просто отправь мне **название песни** или имя исполнителя, "
        "и я найду её в интернете!",
        reply_markup=main_keyboard
    )

@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    await message.answer(
        "📌 **Как пользоваться ботом:**\n"
        "1. Напиши название трека (например: `Miyagi - Utopia`)\n"
        "2. Подожди пару секунд пока бот ищет и скачивает аудио\n"
        "3. Получи MP3-файл прямо в чат!"
    )

@dp.message(F.text == "🎵 Как скачать?")
async def info_handler(message: Message):
    await message.answer("Просто отправь любое текстовое сообщение с названием песни!")

@dp.message(F.text)
async def search_and_send(message: Message):
    query = message.text
    msg = await message.answer(f"🔍 Ищу '{query}' в интернете...")

    try:
        unique_id = str(uuid.uuid4())
        out_template = f"downloads/{unique_id}.%(ext)s"
        expected_filename = f"downloads/{unique_id}.mp3"

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'quiet': True,
            'default_search': 'ytsearch1',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        loop = asyncio.get_running_loop()

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if 'entries' in info and len(info['entries']) > 0:
                    return info['entries'][0].get('title', 'Аудиозапись')
                return "Аудиозапись"

        title = await loop.run_in_executor(None, download)

        if os.path.exists(expected_filename):
            await msg.edit_text("📤 Отправляю файл...")
            audio = FSInputFile(expected_filename)
            await message.answer_audio(audio=audio, title=title)
            await msg.delete()
            
            os.remove(expected_filename)
        else:
            await msg.edit_text("❌ Ошибка при скачивании файла.")

    except Exception as e:
        await msg.edit_text("❌ Произошла ошибка при поиске или скачивании.")
        print(f"Ошибка: {e}")

async def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())