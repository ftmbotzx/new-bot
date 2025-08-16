import motor.motor_asyncio
from info import (
    MONGO_URI, MONGO_NAME, MAINTENANCE_MODE, COLLECTION_NAME,
    MONGO_URI_2, MONGO_NAME_2
)
from datetime import datetime, timedelta

MAX_DOCS_PRIMARY = 9000
BATCH_SIZE = 5000

class Database:
    def __init__(self):
        # Primary DB
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_NAME]
        self.col = self.db["dump"]
        self.media_col = self.db[COLLECTION_NAME]
        self.tasks_collection = self.db["tasks"]
        self.tasks = self.db["tasks"]
        self.jio_collection = self.db['jio_music_files1']
        self.bots = self.db["bots"]
        self.tracks = self.db["tracks"]
        self.track_files = self.db["track_files"]

        self.client2 = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI_2)
        self.db2 = self.client2[MONGO_NAME_2]
        self.jio_collection_backup = self.db2['jio_music_files1']
   
    def new_user(self, id, name):
        return {"id": int(id), "name": name}

    # ----------- Dump cache methods (5000-batch optimized) -------------

    async def save_dump_file_id_by_jio(self, music_id: str):
        """
        Save music_id in batches of 5000 per document.
        Duplicate avoided automatically with $addToSet.
        """
        # Try last doc in primary with < BATCH_SIZE IDs
        doc = await self.jio_collection.find_one(sort=[("_id", -1)])
        if doc and len(doc.get("m", [])) < BATCH_SIZE:
            await self.jio_collection.update_one(
                {"_id": doc["_id"]},
                {"$addToSet": {"m": music_id}}
            )
            return

        # Primary full or no suitable doc → check secondary
        primary_count = await self.jio_collection.count_documents({})
        if primary_count >= MAX_DOCS_PRIMARY:
            doc = await self.jio_collection_backup.find_one(sort=[("_id", -1)])
            if doc and len(doc.get("m", [])) < BATCH_SIZE:
                await self.jio_collection_backup.update_one(
                    {"_id": doc["_id"]},
                    {"$addToSet": {"m": music_id}}
                )
                return
            # create new doc in secondary
            await self.jio_collection_backup.insert_one({"m": [music_id]})
            return

        # Create new doc in primary
        await self.jio_collection.insert_one({"m": [music_id]})

    async def get_dump_file_id_by_jio(self, music_id: str):
        """
        Check if music_id exists in primary, else secondary.
        Returns document if found, else None.
        """
        result = await self.jio_collection.find_one({"m": music_id}, {"_id": 0})
        if result:
            return result
        return await self.jio_collection_backup.find_one({"m": music_id}, {"_id": 0})

    async def get_all_music_ids(self):
        """
        Return all music IDs from primary DB as a flat list.
        """
        cursor = self.jio_collection.find({}, {"_id": 0, "m": 1})
        all_ids = []
        async for doc in cursor:
            all_ids.extend(doc.get("m", []))
        return all_ids

    async def count_music_ids(self):
        """
        Total music ID count in primary DB.
        """
        cursor = self.jio_collection.find({}, {"m": 1})
        total = 0
        async for doc in cursor:
            total += len(doc.get("m", []))
        return total

    # ----------- Existing dump file id system (unchanged) -------------

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
        count = await self.col.count_documents({})
        return count

    async def delete_all_dumps(self) -> int:
        result = await self.col.delete_many({})
        return result.deleted_count

# create instance
db = Database()
