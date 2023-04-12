import logging
from collections.abc import Awaitable, Callable
from copy import deepcopy

from telegram.ext import BasePersistence

# noinspection PyProtectedMember
from telegram.ext._utils.types import (
    BD,
    CD,
    UD,
    CDCData,
    ConversationDict,
    ConversationKey,
)

from mongopersistence.dbhelper import DBMongoHelper, TypeData

BOT_DATA_KEY = 0

NEW_DATA = BD | CD | UD | CDCData | ConversationDict

logger = logging.getLogger(__name__)


def log_data(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
    name: str = func.__name__

    async def wrapper(self: BasePersistence, *args, **kwargs):
        logger.debug(f"Calling {name!r} with {args=}, {kwargs=}")
        res = await func(self, *args, **kwargs)
        logger.debug(f"Result of {name!r} is {res!r}")
        return res

    return wrapper


class MongoPersistence(BasePersistence[BD, CD, UD]):
    def __init__(
        self,
        helper: DBMongoHelper[BD, CD, UD, ConversationDict],
        update_interval: float = 60,
        load_on_flush=True,
    ):
        super().__init__(helper.store_data, update_interval)

        self.helper = helper

        self.load_on_flush = load_on_flush

        self.user_data = helper.user_data
        self.chat_data = helper.chat_data
        self.bot_data = helper.bot_data

        # self.callback_data: TypeData = helper.callback_data
        self.conversations_data = helper.conversations_data

    # [==================================== GENERAL FUNCTIONS ====================================]

    async def get_data(self, type_data: TypeData) -> dict:
        await self.helper.post_init()
        if not type_data.exists():
            return {}
        data = type_data.data
        if not type_data.data:
            post: dict
            for post in await type_data.col.find().to_list(length=None):
                id_ = post.pop("_id")
                data[id_] = post
        return deepcopy(data)

    async def update_data(self, type_data: TypeData, id_: int, new_data: NEW_DATA) -> None:
        await self.helper.post_init()
        if not type_data.exists() or self.load_on_flush or not new_data:
            return
        data = type_data.data
        if data.get(id_) == new_data:
            return
        new_post = {"_id": id_}
        new_post.update(new_data)
        old_post = await type_data.col.find_one({"_id": id_})
        if not old_post:
            await type_data.col.insert_one(new_post)
            return
        if old_post != new_post:
            await type_data.col.replace_one({"_id": id_}, new_post)
        data[id_] = deepcopy(new_data)

    async def refresh_data(self, type_data: TypeData, id_: int, local_data: NEW_DATA) -> None:
        await self.helper.post_init()
        return await self.update_data(type_data, id_, local_data)

    async def drop_data(self, type_data: TypeData, id_: int) -> None:
        await self.helper.post_init()
        if not type_data.exists():
            return
        data = type_data.data
        if data.get(id_):
            data.pop(id_)
            await type_data.col.delete_one({"_id": id_})

    async def load_all_type_data(self, type_data: TypeData) -> None:
        await self.helper.post_init()
        if not type_data.exists():
            return
        data = type_data.data
        for key, item in data.items():
            new_post = {"_id": key}
            new_post.update(item)
            old_post = await type_data.col.find_one({"_id": key})
            if not old_post:
                await type_data.col.insert_one(new_post)
                continue
            if old_post != new_post:
                await type_data.col.replace_one({"_id": key}, new_post)

    # [==================================== USER DATA FUNCTIONS ======================================]

    @log_data
    async def get_user_data(self) -> dict[int, UD]:
        return await self.get_data(self.user_data)

    @log_data
    async def update_user_data(self, user_id: int, data: UD) -> None:
        await self.update_data(self.user_data, user_id, data)

    @log_data
    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        await self.refresh_data(self.user_data, user_id, user_data)

    @log_data
    async def drop_user_data(self, user_id: int) -> None:
        await self.drop_data(self.user_data, user_id)

    # [==================================== BOT DATA FUNCTIONS ======================================]

    @log_data
    async def get_bot_data(self) -> BD:
        await self.helper.post_init()
        if not self.bot_data.exists():
            return
        data = self.bot_data.data
        if data == {}:
            collection = self.bot_data.col
            post: dict = await collection.find_one({"_id": BOT_DATA_KEY})
            if post:
                data = post["content"]
        return deepcopy(data)

    @log_data
    async def update_bot_data(self, data: BD) -> None:
        await self.helper.post_init()
        if not self.bot_data.exists() or self.load_on_flush or data == {}:
            return
        old_data = self.bot_data.data
        if old_data == data:
            return
        collection = self.bot_data.col
        new_post = {"_id": BOT_DATA_KEY, "content": data}
        old_post = await collection.find_one({"_id": BOT_DATA_KEY})
        if not old_post:
            await collection.insert_one(new_post)
            return
        if old_post != new_post:
            await collection.update_one({"_id": BOT_DATA_KEY}, {"$set": {"content": data}})

    @log_data
    async def refresh_bot_data(self, bot_data: BD) -> None:
        return await self.update_bot_data(bot_data)

    # [==================================== CHAT DATA FUNCTIONS ======================================]

    @log_data
    async def get_chat_data(self) -> dict[int, CD]:
        return await self.get_data(self.chat_data)

    @log_data
    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        await self.update_data(self.chat_data, chat_id, data)

    @log_data
    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        await self.refresh_data(self.chat_data, chat_id, chat_data)

    @log_data
    async def drop_chat_data(self, chat_id: int) -> None:
        await self.drop_data(self.chat_data, chat_id)

    # [==================================== CALLBACK DATA FUNCTIONS ======================================]

    async def get_callback_data(self) -> CDCData | None:
        # TODO: create this method
        pass

    async def update_callback_data(self, data: CDCData) -> None:
        # TODO: create this method
        pass

    # [==================================== CONVERSATIONS DATA FUNCTIONS ======================================]

    @log_data
    async def get_conversations(self, name: str) -> ConversationDict:
        await self.helper.post_init()
        if not self.conversations_data.exists():
            return {}

        def string_to_tuple(string: str) -> tuple[int, int]:
            string = string.replace("(", "")
            string = string.replace(")", "")
            first, second = map(int, string.split(","))
            return first, second

        data = self.conversations_data.data
        if not data.get(name):
            post: dict = await self.conversations_data.col.find_one({"_id": name})
            if post:
                post.pop("_id")
                conv_data = {}
                for key_string, item in post.items():
                    conv_data[string_to_tuple(key_string)] = item
                data[name] = conv_data
            else:
                data[name] = {}
        return deepcopy(data.get(name))

    @log_data
    async def update_conversation(self, name: str, key: ConversationKey, new_state: object | None) -> None:
        await self.helper.post_init()
        if self.load_on_flush or not self.conversations_data.exists():
            return
        data: dict[str, dict] = self.conversations_data.data
        if data.setdefault(name, {}).get(key) == new_state:
            return
        data[name][key] = new_state
        collection = self.conversations_data.col
        new_post = {"_id": name, str(key): new_state}
        old_post: dict = await collection.find_one({"_id": name})
        if not old_post:
            await collection.insert_one(new_post)
            return
        if new_post != old_post:
            old_post.update(new_post)
            await collection.replace_one({"_id": name}, old_post)

    # [==================================== FLUSH FUNCTION ======================================]

    @log_data
    async def flush(self) -> None:
        await self.helper.post_init()
        if self.load_on_flush:
            await self.load_all_type_data(self.user_data)
            await self.load_all_type_data(self.chat_data)
            if self.bot_data.exists():
                new_post = {"_id": BOT_DATA_KEY, "content": self.bot_data.data}
                old_post = self.bot_data.col.find_one({"_id": BOT_DATA_KEY})
                if old_post:
                    if old_post != new_post:
                        await self.bot_data.col.update_one({"_id": BOT_DATA_KEY}, {"$set": {"content": self.bot_data}})
                else:
                    await self.bot_data.col.insert_one(new_post)
        self.helper.client.close()
