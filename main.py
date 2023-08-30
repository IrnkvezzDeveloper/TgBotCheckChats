import asyncio
import os
import signal
from pathlib import Path
from zipfile import ZipFile

import pyrogram.types
from pyrogram.types import Chat

import tools
from prisma import Prisma
from TGConvertor.manager.manager import SessionManager

from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from subprocess import Popen
from pyrogram import Client

bot = Bot(
    '6473395844:AAHgNJZVN2AHUaKgLlgWYf01yQC-nS8BID4'
)
dp = Dispatcher(bot, storage=MemoryStorage())

checking_process = []

# STATES


class NewCategoryStates(StatesGroup):
    input_name = State()


class NewChatStates(StatesGroup):
    input_link = State()
    select_category = State()
    input_words = State()


class ManageCategory(StatesGroup):
    input_name = State()
    input_words = State()

class ManageChats(StatesGroup):
    input_words = State()

class AddAccountStates(StatesGroup):
    receive_tdata = State()
    receive_session = State()
    input_number = State()
    input_code = State()
    input_2fa = State()

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
        

@dp.message_handler(commands=['start'], state='*')
async def on_start_cmd(msg: types.Message, state: FSMContext):
    await state.finish()
    await msg.answer("Приветики", reply_markup=Keyboards.get_main_menu_kb())


@dp.message_handler(text='Аккаунты')
async def on_accounts_selected(msg: types.Message, state: FSMContext):
    prisma = Prisma()
    await prisma.connect()
    accounts_count = 0
    accounts = await prisma.telegram_accounts.find_many()
    if accounts is not None:
        accounts_count = len(accounts)
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(text="Добавить аккаунт", callback_data="manage-accounts_add")
        # InlineKeyboardButton(text="Удалить аккаунт", callback_data="manage-accounts_remove")
    )
    await msg.answer(
        f"Кол-во аккаунтов: {accounts_count}\n"
        "Выберите действие",
        reply_markup=kb
    )
    await prisma.disconnect()

@dp.callback_query_handler(text='check-msg_answered')
async def on_msg_checked_answered(msg: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text="✅", callback_data='_')
    )
    await msg.message.edit_reply_markup(kb)

@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'manage-accounts')
async def on_accounts_manage_action(msg: types.CallbackQuery, state: FSMContext):
    _, action = msg.data.split('_')
    match action:
        case 'add':
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(text="TData", callback_data='add-account_tdata'),
                InlineKeyboardButton(text='По номеру телефона', callback_data='add-account_number')
            )
            # kb.row(
            #     InlineKeyboardButton(text="Telethon session", callback_data='add-account_session_telethon'),
            #     InlineKeyboardButton(text="Pyrogram session", callback_data='add-account_session_pyrogram')
            # )
            await msg.message.answer("Выберите способ добавления аккаунта", reply_markup=kb)
        case 'remove':
            ...

@dp.callback_query_handler(lambda c: c.data.split("_")[0] == 'add-account')
async def on_account_add_event(msg: types.CallbackQuery, state: FSMContext):
    match msg.data.split('_')[1]:
        case 'tdata':
            await AddAccountStates.receive_tdata.set()
            await msg.message.answer("Пришлите .zip архив хранящий в себе папку tdata")
        case 'number':
            await AddAccountStates.input_number.set()
            await msg.message.answer("Пожалуйста, введите номер телефона")
        case 'session':
            ...

@dp.message_handler(state=AddAccountStates.input_number)
async def on_number_received(msg: types.Message, state: FSMContext):
    cl = tools.get_client(msg.text, None)
    await cl.connect()
    sent: pyrogram.types.SentCode = await cl.send_code(msg.text)
    await state.update_data({'number': msg.text, 'cl': cl, 'hash': sent.phone_code_hash})
    await msg.answer("Введите код который пришел вам от администратора телеграм")
    await AddAccountStates.input_code.set()

@dp.message_handler(state=AddAccountStates.input_code)
async def on_code_received(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    cl: Client = data.get('cl')
    hash = data.get('hash')
    number = data.get('number')
    try:
        await cl.sign_in(number, hash, msg.text)
        me = await cl.get_me()
        await msg.answer(f"Аккаунт @{me.username} успешно добавлен")
        sess_str = tools.to_string(cl)
        prisma = Prisma()
        await prisma.connect()
        await prisma.telegram_accounts.create({
            'number': number,
            'session_str': sess_str
        })
        await prisma.disconnect()
    except Exception as ex:
        print(ex)
        await msg.answer("Код не верный, повторите попытку")




@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=AddAccountStates.receive_tdata)
async def on_tdata_received(msg: types.Message, state: FSMContext):
    try:
        await msg.document.download(destination='./temp/data.zip')
        with ZipFile('./temp/data.zip', 'r') as fp:
            fp.extractall('./temp/tdatas/')
        sess = SessionManager.from_tdata_folder(Path('./temp/tdatas/tdata/'))
        session_str = sess.to_pyrogram_string()
        cl = tools.get_client('temp', session_str)
        await cl.connect()
        bot_me = await cl.get_me()
        number = bot_me.phone_number
        username = bot_me.username
        await msg.answer(f"Бот @{username} успешно добавлен")
        await state.finish()
        prisma = Prisma()
        await prisma.connect()
        await prisma.telegram_accounts.create(data={
            "number": number.split('+')[-1],
            "session_str": session_str
        })
        await prisma.disconnect()
    except Exception as ex:
        await msg.answer("Tdata является не рабочей. Пришлите другой архив")
        print(ex)
    finally:
        os.remove('./temp/data.zip')
        os.system('rm -r temp')


@dp.message_handler(text='Чаты')
async def on_chats_button(msg: types.Message, state: FSMContext):
    prisma = Prisma()
    await prisma.connect()
    account = await prisma.telegram_accounts.find_first()
    chats = await prisma.chats.find_many()
    await prisma.disconnect()
    kb = InlineKeyboardMarkup()
    _acc: Client = tools.get_client(account.number, account.session_str)
    await _acc.connect()
    for chat in chats:
        _chat = await _acc.get_chat(chat.id)
        kb.insert(
            InlineKeyboardButton(
                text=str(_chat.title),
                callback_data=f"selected-chat_{chat.id}")
        )
    kb.add(
        InlineKeyboardButton(
            text="Добавить чат",
            callback_data="selected-chat_new")
    )
    await msg.answer("Пожалуйста, выберите чат из списка или добавьте новый", reply_markup=kb)


@dp.message_handler(text="Категории")
async def on_categories_button(msg: types.Message, state: FSMContext):
    # get categories from prisma
    prisma = Prisma()
    await prisma.connect()
    categories = await prisma.categories.find_many()
    await prisma.disconnect()
    kb = InlineKeyboardMarkup()
    for item in categories:
        kb.insert(
            InlineKeyboardButton(
                text=item.name,
                callback_data=f"select-category_{item.id}")
        )
    kb.add(
        InlineKeyboardButton(
            text="Создать категорию",
            callback_data="select-category_new")
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
        if data.isdigit():
            prisma = Prisma()
            await prisma.connect()
            category = await prisma.categories.find_first(where={'id': int(data)})
            await prisma.disconnect()
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(text='Изменить название', callback_data='manage-category_name'),
                InlineKeyboardButton(text='Ключевые слова', callback_data='manage-category_words')
            )
            kb.add(
                InlineKeyboardButton(text='Удалить категорию', callback_data='manage-category_remove')
            )
            words_count = 0
            if category.words is not None:
                words_count = len(category.words.split(','))

            await state.update_data({'category_id': category.id})
            await msg.message.answer(
                f"Категория №{category.id}\n"
                f"Название: {category.name}\n"
                f"Ключевых слов: {words_count}",
                reply_markup=kb
            )

        else:
            return


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'manage-category')
async def on_category_manage_event(msg: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id: int = data.get('category_id')
    match msg.data.split('_')[1]:
        case 'name':
            await ManageCategory.input_name.set()
            await msg.message.answer(
                "Введите новое имя для данной категории\n"
                "Отправьте \"Отмена\" если хотите оставить его прежним"
            )
        case 'words':
            prisma = Prisma()
            await prisma.connect()
            category = await prisma.categories.find_first(where={'id': category_id})
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(text='Добавить слово', callback_data='manage-category_word_add'),
                InlineKeyboardButton(text='Удалить слово', callback_data='manage-category_word_remove')
            )
            words = 'Не найдено'
            if category.words is not None:
                words = ', '.join(category.words.split(','))
            await msg.message.answer(
                f"Ключевые слова категории: {category.name}\n\n{words}", reply_markup=kb
            )
            await prisma.disconnect()
        case 'word':
            _, __, act = msg.data.split('_')
            if act == 'add':
                await msg.message.answer(
                    "Пожалуйста, введите список слов которые хотите добавить, "
                    "разделяя каждое через запятую\n\nПример: \n удача,приз,1000к")
            else:
                await msg.message.answer(
                    "Пожалуйста, введите список слов которые хотите добавить, "
                    "разделяя каждое через запятую\n\nПример: \n удача,приз,1000к")
            await ManageCategory.input_words.set()
            await state.update_data({'word-action': act})
        case 'remove':
            prisma = Prisma()
            await prisma.connect()
            await prisma.categories.delete(where={'id': category_id})
            exists_category = await prisma.categories.find_first()
            await prisma.chats.update({'category_id': exists_category.id}, where={'category_id': category_id})
            await prisma.disconnect()
            await msg.message.answer(
                "Категория была успешно удалена\n\n"
                "Чаты привязанные к данной категории были переведены на рандомную категорию"
            )


@dp.message_handler(state=ManageCategory.input_words)
async def on_words_inputted(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("word-action")
    words_to_act = msg.text.split(',')
    prisma = Prisma()
    await prisma.connect()
    category = await prisma.categories.find_first(where={'id': data.get('category_id')})
    exists_words = []
    if category.words is not None:
        exists_words.extend(category.words.split(','))
    match action:
        case 'add':
            for word in words_to_act:
                if word not in exists_words:
                    exists_words.append(word)
        case 'remove':
            for word in words_to_act:
                if word in exists_words:
                    exists_words.remove(word)

    await prisma.categories.update(
        data={'words': ','.join(exists_words)},
        where={'id': category.id}
    )
    await prisma.disconnect()
    await state.finish()
    await msg.answer("Изменения были применены\nВы в главном меню", reply_markup=Keyboards.get_main_menu_kb())


@dp.message_handler(state=ManageCategory.input_name)
async def on_name_changed(msg: types.Message, state: FSMContext):
    if msg.text.lower() == 'отмена':
        await msg.answer("Действие отменено\n\nВы в главном меню", reply_markup=Keyboards.get_main_menu_kb())
        await state.finish()
        return

    data = await state.get_data()
    category_id: int = data.get('category_id')
    prisma = Prisma()
    await prisma.connect()
    await prisma.categories.update({'name': msg.text}, where={'id': category_id})
    await prisma.disconnect()
    await state.finish()
    await msg.answer(
        f"Вы успешно изменили имя категории на {msg.text}\n"
        f"Вы были перемещены в главное меню",
        reply_markup=Keyboards.get_main_menu_kb()
    )


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'selected-chat')
async def on_chat_action(msg: types.CallbackQuery, state: FSMContext):
    _, data = msg.data.split('_')
    if data == 'new':
        await msg.message.answer("Пожалуйста, введите ссылку на чат")
        await NewChatStates.input_link.set()
    else:
        if True:
            prisma = Prisma()
            await prisma.connect()
            rand_cl = await prisma.telegram_accounts.find_first()
            _chat = await prisma.chats.find_first(where={'id': int(data)})
            await prisma.disconnect()
            if rand_cl is None:
                await msg.message.answer("Добавьте хотя бы один телеграм аккаунт")
                await state.finish()
                return
            client = tools.get_client(rand_cl.number, rand_cl.session_str)
            await client.connect()
            chat = await client.get_chat(_chat.id)
            words = 'Не найдено'
            if _chat.words is not None:
                words = len(_chat.words.split(','))
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(text='Удалить чат', callback_data='manage-chats_remove'),
                InlineKeyboardButton(text='Ключевые слова', callback_data='manage-chats_words')
            )
            await state.update_data({'chat_id': _chat.id})
            await msg.message.answer(
                f"Название чата: {chat.title}\n"
                f"Ключевых слов: {words}",
                reply_markup=kb
            )
        else:
            return

@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'manage-chats')
async def on_chats_manage_action(msg: types.CallbackQuery, state: FSMContext):
    _, action = msg.data.split('_')
    data = await state.get_data()
    match action:
        case 'remove':
            prisma = Prisma()
            await prisma.connect()
            await prisma.chats.delete(where={'id': int(data.get('chat_id'))})
            await prisma.disconnect()
            await msg.message.answer("Чат был успешно удален", reply_markup=Keyboards.get_main_menu_kb())
            await state.finish()
        case 'words':
            prisma = Prisma()
            await prisma.connect()
            chat = await prisma.chats.find_first(where={'id': data.get('chat_id')})
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton(text='Добавить слова', callback_data='chat-words_add'),
                InlineKeyboardButton(text='Удалить слова', callback_data='chat-words_remove')
            )
            await msg.message.answer(
                f"Ключевые слова для этого чата: \n\n{chat.words}",
                reply_markup=kb
            )
            await prisma.disconnect()


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'chat-words')
async def on_chat_words_managed(msg: types.CallbackQuery, state: FSMContext):
    _, action = msg.data.split('_')
    await state.update_data({'action': action})
    if action == 'add':
        await msg.message.answer("Введите ключевые слова для добавления разделяя их запятой")
    elif action == 'remove':
        await msg.message.answer("Введите ключевые слова для удаления разделяя их запятой")
    await ManageChats.input_words.set()


@dp.message_handler(state=ManageChats.input_words)
async def on_words_inputted(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    prisma = Prisma()
    await prisma.connect()
    words = msg.text.split(',')
    exists_words = await prisma.chats.find_first(where={'id': data.get('chat_id')})
    exists_words_list = exists_words.split(',')
    if data.get('action') == 'add':
        for word in words:
            if word not in exists_words_list:
                exists_words_list.append(word)
    elif data.get('action') == 'remove':
        for word in words:
            if word in exists_words_list:
                exists_words_list.remove(word)
    await prisma.chats.update(data={'words': ','.join(exists_words_list)}, where={'id': data.get('chat_id')})
    await msg.answer("Действие было успешно выполнено", reply_markup=Keyboards.get_main_menu_kb())
    await state.finish()
    await prisma.disconnect()


@dp.message_handler(state=NewChatStates.input_link)
async def on_chat_link_received(msg: types.Message, state: FSMContext):
    if msg.text.startswith("https://t.me/") or msg.text.startswith("@"):
        prisma = Prisma()
        await prisma.connect()
        random_client = await prisma.telegram_accounts.find_first()
        await prisma.disconnect()
        if random_client is None:
            await msg.answer("Добавьте сначала хоть один телеграм аккаунт!")
            await state.finish()
            return
        rand_cl: Client = tools.get_client(random_client.number, random_client.session_str)
        try:
            await rand_cl.connect()
            chat: Chat = await rand_cl.join_chat(msg.text)
            await state.update_data({
                'chat_id': chat.id,
                'chat_title': chat.title
            })
            await NewChatStates.select_category.set()
            await prisma.connect()
            categories = await prisma.categories.find_many()
            await prisma.disconnect()
            kb = InlineKeyboardMarkup()
            await state.update_data({'invite_link': msg.text})
            for category in categories:
                kb.insert(InlineKeyboardButton(text=category.name, callback_data=f'link-chat_{category.id}'))
            await msg.answer("Пожалуйста, выберите категорию, к которой привязать данный чат", reply_markup=kb)
        except Exception as ex:
            print(ex)
            await msg.answer("Ссылка невалидна. Попробуйте другую")
    else:
        await msg.answer("Введена невалидная ссылка\nПример ссылок\n\nhttps://t.me/+AbCdEf0123456789\n@mychat")


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'link-chat', state=NewChatStates.select_category)
async def on_category_linked(msg: types.CallbackQuery, state: FSMContext):
    _, category_id = msg.data.split('_')
    await state.update_data({'category_id': int(category_id)})
    await NewChatStates.input_words.set()
    await msg.message.answer("Пожалуйста, введите ключевые слова для чата, перечисляя их через запятую.\n\n"
                             "Пример: забота,прибыль,магия")


@dp.message_handler(state=NewChatStates.input_words)
async def on_chat_words_received(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    words = msg.text.split(',')
    prisma = Prisma()
    await prisma.connect()
    await prisma.chats.create({
        'id': data.get('chat_id'),
        'category_id': data.get('category_id'),
        "invite_link": data.get("invite_link"),
        'words': ','.join(words)
    })
    await prisma.disconnect()
    await state.finish()
    await msg.answer(f"Чат {data.get('chat_title')} был успешно добавлен")


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





def on_exit_callback(signal_code, frame):
    print("Program was finished with code ", signal_code)
    for i in checking_process:
        i.kill()
    print("BY InfinityTeam")
    exit(0)


async def on_start_callback():
    env = os.environ
    checking_process.append( Popen(['python', 'account_worker.py'], cwd=os.getcwd(), env=env) )
    actions = [
        asyncio.create_task(dp.start_polling(relax=0.05)),
    ]
    await asyncio.wait(actions)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, on_exit_callback)
    signal.signal(signal.SIGTERM, on_exit_callback)
    signal.signal(signal.SIGQUIT, on_exit_callback)
    asyncio.run(on_start_callback())
