from dataclasses import dataclass,field

from telegram.ext import PersistenceInput

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

@dataclass()
class typedata:

    collection_name : str
    db  : Database

    col : Collection = None
    data : dict = field(default_factory=dict)
    
    def exists(self) -> bool:
        return not self.collection_name is None

    def __post_init__(self) -> None:
        if self.exists():
            self.col = self.db[self.collection_name]

@dataclass()
class DBMongoHelper:

    #TODO: add support for callback_data

    mongo_key : str
    db_name   : str

    name_col_user_data : str = None
    name_col_chat_data : str = None
    name_col_bot_data  : str = None

    #name_col_callback_data : str = None
    name_col_conversations : str = None

    #TODO: add a feature that allows you to ignore dictionary elements using string lists so they don't become persistent

    def __post_init__(self) -> None:
        
        self.client = MongoClient(self.mongo_key)
        self.db     = self.client[self.db_name]

        self.bot_data = typedata(self.name_col_bot_data,self.db)
        self.chat_data = typedata(self.name_col_chat_data,self.db)
        self.user_data = typedata(self.name_col_user_data,self.db)
        #self.callback_data = typedata(self.name_col_callback_data,self.db)
        self.conversations_data = typedata(self.name_col_conversations,self.db)

        self.store_data = PersistenceInput(
            self.bot_data.exists(),
            self.chat_data.exists(),
            self.user_data.exists(),
            False #self.callback_data.exists()
        )