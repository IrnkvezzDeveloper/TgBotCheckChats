from prisma import Prisma
from pyrogram import Client, types, dispatcher, idle
from tools import get_client
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging


logging.basicConfig(level=logging.INFO)
notification_chat_id = 6629502994
token = '6473395844:AAHgNJZVN2AHUaKgLlgWYf01yQC-nS8BID4'
bot = Bot(token=token)


async def main():
    prisma = Prisma()
    await prisma.connect()
    client = await prisma.telegram_accounts.find_first()
    py_cl: Client = get_client(client.number, client.session_str)
    bot_id = await bot.get_me()

    @py_cl.on_message()
    async def on_message_received(cl_, msg: types.Message):
        # await msg.forward(msg.chat.id)
        chats = await prisma.chats.find_many()
        ids = [i.id for i in chats]
        if msg.from_user.id == bot_id.id:
            return
        if msg.chat.id in ids:
            logging.info("Нашел чат в ID базы данных")
            cur_chat = await prisma.chats.find_first(where={'id': msg.chat.id})
            words = cur_chat.words.split(',')
            logging.info(words)

            for word in words:
                if msg.text.find(word) != -1:
                    logging.info("Нашел СЛОВО")
                    kb = InlineKeyboardMarkup()
                    kb.add(InlineKeyboardButton(text='Проверено?', callback_data='check-msg_answered'))
                    await bot.send_message(
                        notification_chat_id,  # TEMP !!!!
                        f"Найдено ключевое слово: {word}!\n\n"
                        f"{msg.text}\n"
                        f"От пользователя @{msg.from_user.username}\n\n"
                        f"Link -> {cur_chat.invite_link}",
                        reply_markup=kb
                    )
                    continue
    async with py_cl:
        await idle()
    await prisma.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
