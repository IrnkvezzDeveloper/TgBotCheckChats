#pylint:disable=C0115
import asyncio
import signal
from prisma import Prisma
from account_worker import Worker

from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup


bot = Bot(
    '6473395844:AAHgNJZVN2AHUaKgLlgWYf01yQC-nS8BID4',
    parse_mode=types.ParseMode.MARKDOWN_V2
)
dp = Dispatcher(bot, storage=MemoryStorage())
worker = Worker(bot)

# STATES

class NewCategoryStates(StatesGroup):
    input_name = State()

#


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

        
@dp.message_handler(text='Чаты')
async def on_chats_button(msg: types.Message, state: FSMContext):
        chats = [
            {
                "id": 0,
                "chat_name": "Автолюбители москва",
                "category_id": 0,
                "words": "дтп,погиб,авария"
            }
        ]
        kb = InlineKeyboardMarkup()
        for chat in chats:
            kb.insert(
                InlineKeyboardButton(text=chat.get("name"), callback_data=f"selected-chat_{chat.get('id')}")
            )
        kb.add(
            InlineKeyboardButton(text="Добавить чат", callback_data="selected-chat_new")
        )
        await msg.answer("Пожалуйста, выберите чат из списка или добавьте новый", reply_markup=kb)
        
        

@dp.message_handler(text="Категории")
async def on_categories_button(msg: types.Message, state: FSMContext):
	# get categories from prisma
	categories = [
	    {
	        "id":0,
	        "name": "testCategory"
	    }
	]
	kb = InlineKeyboardMarkup()
	for item in categories:
	    kb.insert(
	        InlineKeyboardButton(text=item.get('name'), callback_data=f"select-category_{item.get('id')}")
	    )
	kb.add(
	    InlineKeyboardButton(text="Создать категорию", callback_data="select-category_new")
	)
	await msg.answer(
	    text="Выберите категорию или создайте новую",
	    reply_markup=kb
	)
	

@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'select-category')
async def category_actions(msg: types.CallbackQuery, state: FSMContext):
    _, data = msg.data.split('_')
    if data == 'new':
        await msg.message.answer("Пожалуйста, введите имя категории")
        await NewCategoryStates.input_name.set()
    else:
        if data.digist():
            ...
        else:
            return


@dp.message_handler(state=NewCategoryStates.input_name)
async def new_category_name(msg: types.Message, state: FSMContext):
    name_of_category = msg.text
    prisma = Prisma()
    await prisma.connect()
    await prisma.categories.create({
        'name': name_of_category
    })
    await msg.answer(f"Категория {name_of_category} успешно создана", reply_markup=Keyboards.get_main_menu_kb())
    await state.finish()
   

@dp.message_handler(commands=['start'])
async def on_start_cmd(msg: types.Message, state: FSMContext):
    await msg.answer("Приветики", reply_markup=Keyboards.get_main_menu_kb())


def on_exit_callback(signal_code, frame):
    print("Program was finished with code ", signal_code)
    print("BY InfinityTeam")
    exit(0)

async def on_start_callback():
    actions = [
        asyncio.create_task(dp.start_polling(relax=0.05)),
        asyncio.create_task(worker.polling()),
    ]
    await asyncio.wait(actions)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, on_exit_callback)
    signal.signal(signal.SIGTERM, on_exit_callback)
    signal.signal(signal.SIGQUIT, on_exit_callback)
    asyncio.run(on_start_callback())
