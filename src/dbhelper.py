
from typing import Dict, Optional
from dataclasses import dataclass

from telegram.ext import PersistenceInput

from pymongo import MongoClient
from pymongo.collection import Collection

@dataclass(frozen=True)
class DBMongoHelper:

    mongo_key : str
    db_name   : str

    bot_data: bool = True
    chat_data: bool = True
    user_data: bool = True
    callback_data: bool = True

    name_col_user_data : str = None
    name_col_chat_data : str = None
    name_col_bot_data  : str = None

    name_col_callback_data : str = None
    name_col_conversations : str = None

    def __post_init__(self) -> None:
        self.store_data = PersistenceInput(
            self.bot_data,
            self.chat_data,
            self.user_data,
            self.callback_data
        )
        self.client = MongoClient(self.mongo_key)
        self.db     = self.client[self.db_name]
    
    def generate_user_data_col(self) -> Optional[Collection]:
        if self.store_data.user_data:
            return self.db[self.name_col_user_data]

    def generate_chat_data_col(self) -> Optional[Collection]:
        if self.store_data.chat_data:
            return self.db[self.name_col_chat_data]

    def generate_bot_data_col(self) -> Optional[Collection]:
        if self.store_data.bot_data:
            return self.db[self.name_col_bot_data]

    def generate_callback_data_col(self) -> Optional[Collection]:
        if self.store_data.callback_data:
            return self.db[self.name_col_callback_data]

    def generate_conversations_data_col(self) -> Optional[Collection]:
        if self.name_col_conversations:
            return self.db[self.name_col_user_data]