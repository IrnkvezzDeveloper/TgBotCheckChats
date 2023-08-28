import asyncio
import signal
from prisma import Prisma

from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

bot = Bot(
    '6473395844:AAHgNJZVN2AHUaKgLlgWYf01yQC-nS8BID4',
    parse_mode=types.ParseMode.MARKDOWN_V2
)
dp = Dispatcher(bot, storage=MemoryStorage())


class Keyboards:
    @staticmethod
    def get_main_menu_kb():
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(
            KeyboardButton(text='Категории'),
            KeyboardButton(text='Чаты')
        )
        kb.add(
            KeyboardButton(text='Аккаунты')
        )
        return kb


@dp.message_handler(commands=['start'])
async def on_start_cmd(msg: types.Message, state: FSMContext):
    await msg.answer("Приветики", reply_markup=Keyboards.get_main_menu_kb())


def on_exit_callback(signal_code, frame):
    print("Program was finished with code ", signal_code)
    print("BY InfinityTeam")
    exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, on_exit_callback)
    signal.signal(signal.SIGTERM, on_exit_callback)
    signal.signal(signal.SIGQUIT, on_exit_callback)
    asyncio.run(dp.start_polling(relax=0.05))
