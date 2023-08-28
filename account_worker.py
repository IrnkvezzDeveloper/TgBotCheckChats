from pathlib import Path
from prisma import Prisma
from pyrogram import Client
from aiogram import Bot
import asyncio
import itertools
from TGConvertor.manager.manager import SessionManager


class Worker:
    def __init__(self, bot):
        self.chats = []
        self.accounts = []
        self.bot = bot

    async def load_data(self):
        prisma = Prisma()
        await prisma.connect()
        chats = await prisma.chats.find_many()
        accounts = await prisma.telegram_accounts.find_many()
        self.chats.extend(chats)
        self.accounts.extend(accounts)
        await prisma.disconnect()

    @property
    def get_chats_chunks(self):
        return [self.chats[i:i + len(self.accounts)] for i in range(0, len(self.chats), len(self.accounts))]

    def get_tasks(self):
        chat_chunks = self.get_chats_chunks
        ret_tasks = []
        for idx, account in enumerate(self.accounts):
            worker = AccountWorker(
                Client(
                    account.get('number'),
                    api_id=6,
                    api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
                    device_model="Samsung SM-G998B",
                    system_version="SDK 31",
                    app_version="8.4.1 (2522)",
                    lang_code="en",
                    session_string=account.get("session_str")
                ),
                chat_chunks[idx],
                self.bot
            )
            ret_tasks.append(
                asyncio.create_task(worker.create_work())
            )
        return ret_tasks


class AccountWorker:
    def __init__(self, account: Client, chats: list, bot: Bot):
        self.account: Client = account
        self.chats = chats
        self.bot = Bot

    async def create_work(self):
        ...
