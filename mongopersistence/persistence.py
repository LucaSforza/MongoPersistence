from dataclasses import dataclass,field
from copy import deepcopy
from typing import Dict, Optional

from telegram.ext import BasePersistence,PersistenceInput
from telegram.ext._utils.types import BD, CD, UD, CDCData, ConversationDict, ConversationKey 

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

BOT_DATA_KEY = 0

@dataclass()
class TypeData:

    collection_name : str
    db  : Database

    col  : Collection = None
    data : dict = field(default_factory=dict)
    
    def exists(self) -> bool:
        return not self.collection_name is None

    def __post_init__(self) -> None:
        if self.exists():
            self.col = self.db[self.collection_name]

class MongoPersistence(BasePersistence[BD,CD,UD]):

    def __init__(
            self,
            mongo_key: str,
            db_name: str,
            name_col_bot_data: str = None,
            name_col_chat_data:str = None,
            name_col_user_data:str = None,
            #name_col_callback_data:str = None,
            name_col_conversations:str = None,
            update_interval: float = 60,
            load_on_flush = False
        ):
        
        #TODO: add support for callback_data
        #TODO: add a feature that allows you to ignore dictionary elements using string lists so they don't become persistent
        
        self.client = MongoClient(mongo_key)
        self.db     = self.client[db_name]

        self.bot_data = TypeData(name_col_bot_data,self.db)
        self.chat_data = TypeData(name_col_chat_data,self.db)
        self.user_data = TypeData(name_col_user_data,self.db)
        #self.callback_data = TypeData(name_col_callback_data,self.db)
        self.conversations_data = TypeData(name_col_conversations,self.db)

        self.store_data = PersistenceInput(
            self.bot_data.exists(),
            self.chat_data.exists(),
            self.user_data.exists(),
            False #self.callback_data.exists()
        )
                
        super().__init__(self.store_data, update_interval)

        self.load_on_flush = load_on_flush

# [================================================ GENERAL FUNCTIONS ==================================================]

    def get_data(self,type_data: TypeData) -> dict:       
        if not type_data.exists():
            return
        if type_data.data == {}:
            data = type_data.data
            post : dict
            for post in type_data.col.find():
                id = post.pop('_id')
                data[id] = post
        return deepcopy(data)

    def update_data(self,type_data: TypeData,id,new_data) -> None:
        if not type_data.exists() or self.load_on_flush or new_data == {}:
            return
        data = type_data.data
        if data.get(id) == new_data:
            return
        new_post = {'_id':id}
        new_post.update(new_data)
        old_post = type_data.col.find_one({"_id":id})
        if not old_post:
            type_data.col.insert_one(new_post)
            return
        if old_post != new_post:
            type_data.col.replace_one({'_id':id},new_post)
        data[id] = new_data
    
    def refresh_data(self,type_data: TypeData,id,local_data: dict) -> None:
        if not type_data.exists() or self.load_on_flush:
            return
        data = type_data.data
        post : dict = type_data.col.find_one({"_id":id})
        if not post:
            return
        post.pop('_id')
        if post != local_data:
            local_data.update(post)
            data[id] = deepcopy(local_data)

    def drop_data(self,type_data: TypeData,id) -> None:
        if not type_data.exists():
            return
        data = type_data.data
        if data.get(id):
            data.pop(id)
            type_data.col.delete_one({'_id':id})

    def load_all_type_data(self,type_data: TypeData) -> None:
        if not type_data.exists():
            return
        data = type_data.data
        for key,item in data.items():
            new_post = {'_id':key}
            new_post.update(item)
            old_post = type_data.col.find_one({'_id':key})
            if not old_post:
                type_data.col.insert_one(new_post)
                continue
            if old_post != new_post:
                type_data.col.replace_one({'_id':key},new_post)

# [================================================ USER DATA FUNCTIONS ==================================================]

    async def get_user_data(self) -> Dict[int, UD]:
        return self.get_data(self.user_data)

    async def update_user_data(self, user_id: int, data: UD) -> None:
        self.update_data(self.user_data,user_id,data)
        
    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        self.refresh_data(self.user_data,user_id,user_data)

    async def drop_user_data(self, user_id: int) -> None:
        self.drop_data(self.user_data,user_id)

# [================================================ BOT DATA FUNCTIONS ==================================================]

    async def get_bot_data(self) -> BD:
        if not self.bot_data.exists():
            return
        data = self.bot_data.data
        if data == {}:
            collection = self.bot_data.col
            post: dict = collection.find_one({'_id':BOT_DATA_KEY})
            if post:
                data = post['content']
        return deepcopy(data)

    async def update_bot_data(self, data: BD) -> None:
        if not self.bot_data.exists() or self.load_on_flush or data == {}:
            return
        old_data = self.bot_data.data
        if old_data == data:
            return
        collection = self.bot_data.col
        old_data = data
        new_post = {'_id':BOT_DATA_KEY,'content':data}
        old_post = collection.find_one({"_id":BOT_DATA_KEY})
        if not old_post:
            collection.insert_one(new_post)
            return
        if old_post != new_post:
            collection.update_one({'_id':BOT_DATA_KEY},{'$set':{'content':data}})

    async def refresh_bot_data(self, bot_data: BD) -> None:
        if self.load_on_flush or not self.bot_data.exists():
            return
        post : dict = self.bot_data.col.find_one({'_id':BOT_DATA_KEY})
        if post:
            external_data = post.get('content')
            if external_data != bot_data:
                self.bot_data.data = external_data
                bot_data: dict.update(external_data)


# [================================================ CHAT DATA FUNCTIONS ==================================================]

    async def get_chat_data(self) -> Dict[int, CD]:
        return self.get_data(self.chat_data)

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        self.update_data(self.chat_data,chat_id,data)

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        self.refresh_data(self.chat_data,chat_id,chat_data)

    async def drop_chat_data(self, chat_id: int) -> None:
        self.drop_data(self.chat_data,chat_id)

# [================================================ CALLBACK DATA FUNCTIONS ==================================================]

    async def get_callback_data(self) -> Optional[CDCData]:
        #TODO: create this method
        pass

    async def update_callback_data(self, data: CDCData) -> None:
        #TODO: create this method
        pass

# [================================================ CONVERSATIONS DATA FUNCTIONS ==================================================]

    async def get_conversations(self, name: str) -> ConversationDict:
        if not self.conversations_data.exists():
            return

        def string_to_tuple(string: str) -> tuple[int,int]:
            string = string.replace('(','')
            string = string.replace(')','')
            return tuple(map(int,string.split(',')))

        data = self.conversations_data.data
        if not data.get(name):
            post: dict = self.conversations_data.col.find_one({'_id':name})
            if post:
                post.pop('_id')
                conv_data = dict()
                for key_string,item in post.items():
                    conv_data[string_to_tuple(key_string)] = item
                data[name] = conv_data
            else:
                data[name] = dict()
        return deepcopy(data.get(name))

    async def update_conversation(self, name: str, key: ConversationKey, new_state: Optional[object]) -> None:
        if self.load_on_flush or not self.conversations_data.exists():
            return
        data: dict[str,dict] = self.conversations_data.data
        if data.setdefault(name,{}).get(key) == new_state:
            return
        data[name][key] = new_state
        collection = self.conversations_data.col
        new_post = {'_id':name,str(key):new_state}
        old_post: dict = collection.find_one({'_id':name})
        if not old_post:
            collection.insert_one(new_post)
            return
        if new_post!=old_post:
            old_post.update(new_post)
            collection.replace_one({'_id':name},old_post)
        

# [================================================ FLUSH FUNCTION ==================================================]

    async def flush(self) -> None:
        if self.load_on_flush:
            self.load_all_type_data(self.user_data)
            self.load_all_type_data(self.chat_data)
            if self.bot_data.exists():
                new_post = {'_id':BOT_DATA_KEY,'content':self.bot_data.data}
                old_post = self.bot_data.col.find_one({'_id':BOT_DATA_KEY})
                if old_post:
                    if old_post!=new_post:
                        self.bot_data.col.update_one({'_id':BOT_DATA_KEY},{'$set':{'content':self.bot_data}})
                else:
                    self.bot_data.col.insert_one(new_post)
        self.client.close()