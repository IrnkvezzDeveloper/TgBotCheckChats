from pyrogram import Client
from aiogram import Bot
import asyncio
import itertools

class Worker:
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.accounts: list = []
        self.is_stop = False
        self.chats: list = []
        

    def chunker(self, seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))
        
    async def polling(self):
        if len(self.accounts) == 0:
            await self.load_accounts()
        if len(self.chats) == 0:
            await self.load_chats()
        chunks = self.chunker(self.chats, len(self.accounts))
        while self.is_stop is False:
            async for idx, chunk in enumerate(chunks):
                tg_account: Client = Client(session_string=self.accounts[idx].get("session_string"))
                history = await tg_account.get_chat_history(chat_id=chunk.get("chat_id") ,limit=10)
                async for msg in history:
                    if msg.text in chunk.get("keys"):
                        async for chat in self.get_chats():
                            await self.bot.send_message(
                                "Обнаружено сообщение с ключевым словом!\n"
                                "Текст сообщения:\n\n"
                                "" + msg.text
                                "\n\n"
                                "Автор: "
                                "@" + msg.username
                            )
            await asyncio.sleep(0.05)
        
    async def load_accounts(self):
        ...
    
    async def load_chats(self):
        ... 
       