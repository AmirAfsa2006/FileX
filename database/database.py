"""Asynchronous MongoDB user repository for FileX."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from config import DATABASE_URL, DB_NAME

dbclient = AsyncIOMotorClient(DATABASE_URL)
database = dbclient[DB_NAME]
user_data = database["users"]


async def present_user(user_id: int) -> bool:
    return await user_data.find_one({"_id": user_id}, {"_id": 1}) is not None


async def add_user(user_id: int) -> None:
    await user_data.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"_id": user_id}},
        upsert=True,
    )


async def full_userbase() -> list[int]:
    return await user_data.distinct("_id")


async def del_user(user_id: int) -> None:
    await user_data.delete_one({"_id": user_id})