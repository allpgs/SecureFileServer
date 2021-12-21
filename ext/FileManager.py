import time
import aiosqlite
from discord.ext import tasks
import asyncio
from os import path, remove
from datetime import datetime
from config import file_expire_time
import aiofiles
import pickle

class FileManager:
    def __init__(self) -> None:
        self.ready = False
        self.files = {}
        self.search_amount = {}
        self.total_downloads = 0
        self.auto_saving = False
        asyncio.get_event_loop().create_task(self.setup())
    
    async def setup(self):
        if path.exists("./searches.bin"):
            try:
                async with aiofiles.open("./searches.bin", "rb") as f:
                    self.search_amount = pickle.loads(await f.read())
            except Exception as e:
                print(f"Error while loading searches: {e}")
                remove("./searches.bin")

        for downloads in self.search_amount.values():
            self.total_downloads += downloads

        print(f"Total downloads: {self.total_downloads}")
    
        if not path.exists("./files.db"):
            self.db = await aiosqlite.connect("files.db")
            await self.db.execute("CREATE TABLE files (filename text, uploader text, expire_at LONG)")
            await self.db.commit()
        else:
            self.db = await aiosqlite.connect("files.db")
        
        cursor = await self.db.execute("SELECT * FROM files")

        for row in await cursor.fetchall():
            self.files[row[0]] = row[2]
        
        await cursor.close()

        self.del_loop.start()
        self.save_searches.start()

        self.ready = True
        print("Ready.")
    
    async def wait_until_save_ends(self):
        while self.auto_saving:
            await asyncio.sleep(1)
    
    @tasks.loop(seconds=60)
    async def save_searches(self):
        await self.wait_until_save_ends()
        
        self.auto_saving = True
        async with aiofiles.open("searches.bin", "wb") as f:
            await f.write(pickle.dumps(self.search_amount))
        self.auto_saving = False

    @tasks.loop(hours=24)
    async def del_loop(self):
        await self.delete_expired()

    async def delete_expired(self):
        await self.wait_until_save_ends()
        self.auto_saving = True
        async with aiofiles.open("./searches.bin", "wb") as f:
            await f.write(pickle.dumps(self.search_amount))

        filenames = self.files.copy().keys()
        timestamp = datetime.now().timestamp()

        for filename in filenames:
            if self.files[filename] < timestamp:
                await self.db.execute("DELETE FROM files WHERE filename=?", (filename,))
                del self.files[filename]

                try:
                    remove("./files/" + filename)
                except:
                    pass

        await self.db.commit()
        self.auto_saving = False

    async def wait_until_ready(self):
        while not self.ready:
            await asyncio.sleep(1)
    
    def wait_until_ready_sync(self):
        while not self.ready:
            time.sleep(1)

    async def addfile(self, filename: str, uploader: str) -> None:
        await self.wait_until_ready()

        await self.db.execute("INSERT INTO files VALUES (?, ?, ?)", (filename, uploader, datetime.now().timestamp() + (86400 * file_expire_time)))
        await self.db.commit()
    
    def get_seaches(self, filename) -> int:
        return self.search_amount[filename] if self.search_amount.__contains__(filename) else 0
    
    def add_searches(self, filename) -> int:
        self.total_downloads += 1
        self.search_amount[filename] = self.search_amount[filename] + 1 if self.search_amount.__contains__(filename) else 1
        return self.search_amount[filename]
    
    def total_searches(self) -> int:
        return self.total_downloads
    
    def total_searches_str(self) -> str:
        return str(self.total_downloads) if self.total_downloads > 0 else "측정 중입니다."