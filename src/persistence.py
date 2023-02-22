from dbhelper import *

from copy import deepcopy
from typing import Dict, Optional

from telegram.ext import BasePersistence
from telegram.ext._utils.types import BD, CD, UD, CDCData, ConversationDict, ConversationKey 

from pymongo.collection import Collection

BOT_DATA_KEY = 0

class MongoPersistence(BasePersistence[BD,CD,UD]):

    def __init__(self,helper: DBMongoHelper,update_interval: float = 60,load_on_flush = True):
        super().__init__(helper.store_data, update_interval)

        self.helper = helper

        self.load_on_flush = load_on_flush

        self.col_user = helper.generate_user_data_col()
        self.col_chat = helper.generate_chat_data_col()
        self.col_bot  = helper.generate_bot_data_col()

        self.col_callback      = helper.generate_callback_data_col()
        self.col_conversations = helper.generate_conversations_data_col()

        self.user_data : dict = None
        self.chat_data : dict = None
        self.bot_data  : BD   = None

        self.callback_data      = None
        self.conversations_data = None

# [================================================ GENERAL FUNCTIONS ==================================================]

    def _get_data(self,type_data,collection: Collection) -> dict:
        if not type_data:
            type_data = dict()
            post : dict
            for post in collection.find():
                id = post.pop('_id')
                type_data[id] = post
        return deepcopy(type_data)

    def _update_data(self,type_data,collection: Collection,id,data) -> None:
        if not self.load_on_flush:
            return
        if type_data is None:
            type_data = dict()
        if type_data.get(id) == data:
            return
        type_data[id] = data
        new_post = {'_id':id}
        new_post.update(data)
        old_post = collection.find_one({"_id":id})
        if not old_post:
            collection.insert_one(new_post)
            return
        if old_post != new_post:
            collection.replace_one({'_id':id},new_post)
    
    def _refresh_data(self,type_data,collection: Collection,id,local_data) -> None:
        if not self.load_on_flush:
            return
        if not type_data:
            type_data = dict()
        post : dict = collection.find_one({"_id":id})
        if not post:
            return
        post.pop('_id')
        if post != local_data:
            local_data = post
            type_data[id] = post

    def _drop_data(self,type_data: dict,collection: Collection,id) -> None:
        if type_data.get(id):
            type_data.pop(id)
            collection.delete_one({'_id':id})

    def _load_all_type_data(self,type_data: dict,collection: Collection) -> None:
        if not type_data:
            return
        for key,item in type_data.items():
            new_post = {'_id':key}
            new_post.update(item)
            old_post = collection.find_one({'_id':key})
            if not old_post:
                collection.insert_one(new_post)
                continue
            if old_post != new_post:
                collection.replace_one({'_id':key},new_post)

# [================================================ USER DATA FUNCTIONS ==================================================]

    async def get_user_data(self) -> Dict[int, UD]:
        return self._get_data(self.user_data,self.col_user)

    async def update_user_data(self, user_id: int, data: UD) -> None:
        self._update_data(self.user_data,self.col_user,user_id,data)
        
    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        self._refresh_data(self.user_data,self.col_user,user_id,user_data)

    async def drop_user_data(self, user_id: int) -> None:
        self._drop_data(self.user_data,self.col_user,user_id)

# [================================================ BOT DATA FUNCTIONS ==================================================]

    async def get_bot_data(self) -> BD:
        if not self.bot_data:
            post: dict = self.col_bot.find_one({'_id':BOT_DATA_KEY})
            if post:
                self.bot_data = post['content']
            else:
                self.bot_data = dict()
        return deepcopy(self.bot_data)

    async def update_bot_data(self, data: BD) -> None:
        if not self.load_on_flush:
            return
        if self.bot_data is None:
            self.bot_data = self.get_bot_data()
        if self.bot_data == data:
            return
        self.bot_data = data
        new_post = {'_id':BOT_DATA_KEY}
        new_post.update({'content':data})
        old_post = self.col_bot.find_one({"_id":BOT_DATA_KEY})
        if not old_post:
            self.col_bot.insert_one(new_post)
            return
        if old_post != new_post:
            self.col_bot.update_one({'_id':BOT_DATA_KEY},{'$set':{'content':data}})

    async def refresh_bot_data(self, bot_data: BD) -> None:
        if not self.load_on_flush:
            return
        if self.bot_data is None:
            self.bot_data = self.get_bot_data()
        post : dict = self.col_bot.find_one({'_id':BOT_DATA_KEY})
        if post:
            external_data = post.get('content')
            if external_data != bot_data:
                self.bot_data = external_data
                bot_data = external_data


# [================================================ CHAT DATA FUNCTIONS ==================================================]

    async def get_chat_data(self) -> Dict[int, CD]:
        return self._get_data(self.chat_data,self.col_chat)

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        self._update_data(self.chat_data,self.col_chat,chat_id,data)

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        self._refresh_data(self.chat_data,self.col_chat,chat_id,chat_data)

    async def drop_chat_data(self, chat_id: int) -> None:
        self._drop_data(self.chat_data,self.col_chat,chat_id)

# [================================================ CALLBACK DATA FUNCTIONS ==================================================]

    async def get_callback_data(self) -> Optional[CDCData]:
        #TODO: create this method
        pass

    async def update_callback_data(self, data: CDCData) -> None:
        #TODO: create this method
        pass

# [================================================ CONVERSATIONS DATA FUNCTIONS ==================================================]

    async def get_conversations(self, name: str) -> ConversationDict:
        #TODO: create this method
        pass

    async def update_conversation(self, name: str, key: ConversationKey, new_state: Optional[object]) -> None:
        #TODO: create this method
        pass

# [================================================ FLUSH FUNCTION ==================================================]

    async def flush(self) -> None:
        if self.load_on_flush:
            self._load_all_type_data(self.user_data,self.col_user)
            self._load_all_type_data(self.chat_data,self.col_chat)
            if self.bot_data:
                new_post = {'_id':BOT_DATA_KEY,'content':self.bot_data}
                old_post = self.col_bot.find_one({'_id':BOT_DATA_KEY})
                if old_post:
                    if old_post!=new_post:
                        self.col_bot.update_one({'_id':BOT_DATA_KEY},{'$set':{'content':self.bot_data}})
                else:
                    self.col_bot.insert_one(new_post)
        self.helper.client.close()