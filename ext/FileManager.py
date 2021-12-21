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
        asyncio.get_event_loop().create_task(self.setup())
    
    async def setup(self):
        if path.exists("./searches.bin"):
            try:
                async with aiofiles.open("./searches.bin", "rb") as f:
                    self.search_amount = pickle.loads(await f.read())
            except:
                remove("./searches.bin")

        for filename, downloads in self.search_amount:
            self.total_downloads += downloads
    
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
        self.ready = True

    @tasks.loop(hours=24)
    async def del_loop(self):
        await self.delete_expired()

    async def delete_expired(self):
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

    async def wait_until_ready(self):
        while not self.ready:
            await asyncio.sleep(1)

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