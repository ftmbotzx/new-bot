import motor.motor_asyncio
from info import (
    MONGO_URI, MONGO_NAME, MAINTENANCE_MODE, COLLECTION_NAME,
    MONGO_URI_2, MONGO_NAME_2
)
from datetime import datetime, timedelta

MAX_DOCS_PRIMARY = 300000

class Database:
    def __init__(self):
        # Primary DB
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_NAME]
        self.col = self.db["dump"]
        self.media_col = self.db[COLLECTION_NAME]
        self.tasks_collection = self.db["tasks"]
        self.tasks = self.db["tasks"]
        self.jio_collection = self.db['jio_music_files']
        self.bots = self.db["bots"]
        self.tracks = self.db["tracks"]
        self.track_files = self.db["track_files"]

        # Secondary DB
        self.client2 = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI_2)
        self.db2 = self.client2[MONGO_NAME_2]
        self.jio_collection_backup = self.db2['jio_music_files']

    def new_user(self, id, name):
        return {"id": int(id), "name": name}

    # ----------- Dump cache methods -------------
    async def save_dump_file_id_by_jio(self, music_id: str, data: dict):
        """
        Save or update music file data by music_id
        Primary DB me max 3 lakh docs tak save karega,
        uske baad secondary DB me save karega.
        """
        data['updated_at'] = datetime.utcnow()

        primary_count = await self.jio_collection.count_documents({})
        if primary_count < MAX_DOCS_PRIMARY:
            await self.jio_collection.update_one(
                {"music_id": music_id},
                {"$set": data},
                upsert=True
            )
        else:
            await self.jio_collection_backup.update_one(
                {"music_id": music_id},
                {"$set": data},
                upsert=True
            )

    async def get_dump_file_id_by_jio(self, music_id: str):
        """
        Get music file data by music_id
        Pehle primary DB me check karega, agar na mile to secondary DB me check karega.
        """
        result = await self.jio_collection.find_one({"music_id": music_id})
        if result:
            return result
        return await self.jio_collection_backup.find_one({"music_id": music_id})

    async def save_dump_file_id(self, track_id: str, file_id: str):
        await self.col.update_one(
            {"track_id": track_id},
            {"$set": {"file_id": file_id}},
            upsert=True
        )

    async def get_dump_file_id(self, track_id: str):
        doc = await self.col.find_one({"track_id": track_id})
        if doc and "file_id" in doc:
            return doc["file_id"]
        return None

    async def get_all_db(self) -> int:
        """Returns total number of dump entries in the primary database."""
        count = await self.col.count_documents({})
        return count

    async def delete_all_dumps(self) -> int:
        """Deletes all dump entries and returns how many were deleted."""
        result = await self.col.delete_many({})
        return result.deleted_count


# create instance
db = Database()
