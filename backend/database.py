"""
MongoDB connection and collection helpers.
"""
import os
from pymongo import MongoClient
from pymongo.database import Database

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "enrollment_agent")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db() -> Database:
    return get_client()[DB_NAME]


def candidates_col():
    return get_db()["candidates"]


def conversations_col():
    return get_db()["conversations"]


def events_col():
    return get_db()["events"]
