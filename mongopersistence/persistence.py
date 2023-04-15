import asyncio
import logging
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import CollectionInvalid
from telegram.ext import BasePersistence, PersistenceInput

# noinspection PyProtectedMember
from telegram.ext._utils.types import (
    BD,
    CD,
    UD,
    CDCData,
    ConversationDict,
    ConversationKey,
)

BOT_DATA_KEY = 0

NEW_DATA = BD | CD | UD | CDCData | ConversationDict

logger = logging.getLogger(__name__)
D = TypeVar("D", bound=dict)
_ConvD = TypeVar("_ConvD", bound=ConversationDict)


def log_data(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
    name: str = func.__name__

    async def wrapper(self: BasePersistence, *args, **kwargs):
        logger.debug(f"Calling {name!r} with {args=}, {kwargs=}")
        res = await func(self, *args, **kwargs)
        logger.debug(f"Result of {name!r} is {res!r}")
        return res

    return wrapper


@dataclass
class TypeData(Generic[D]):
    collection_name: str
    db: AsyncIOMotorDatabase

    col: AsyncIOMotorCollection = None
    data: dict = field(default_factory=dict)

    create_col: bool = False

    to_ignore: list[str] = field(default_factory=list)

    def filter(self, data: dict[str, Any]) -> dict[str, Any]:
        for item in self.to_ignore:
            data.pop(item, None)
        return data

    def exists(self) -> bool:
        return self._exist

    def __post_init__(self) -> None:
        self._exist = self.collection_name is not None

    async def post_init(self) -> None:
        self._exist = False
        if self.collection_name is None:
            return
        if self.create_col:
            logger.info(f"Creating collection {self.collection_name!r}...")
            try:
                self.col = await self.db.create_collection(self.collection_name)
            except CollectionInvalid as e:
                if e.args[0] != f"collection {self.collection_name} already exists":
                    raise e
                logger.info(f"Collection {self.collection_name!r} already exists")
                self.col = self.db.get_collection(self.collection_name)
        else:
            logger.info(f"Getting collection {self.collection_name!r}...")
            self.col = self.db.get_collection(self.collection_name)
        self._exist = True


class MongoPersistence(BasePersistence[BD, CD, UD]):
    def __init__(
        self,
        mongo_url: str,
        db_name: str,
        name_col_user_data: str | None = None,
        name_col_chat_data: str | None = None,
        name_col_bot_data: str | None = None,
        name_col_conversations_data: str | None = None,
        # name_col_callback_data: str | None = None,
        create_col_if_not_exist: bool = False,
        ignore_general_data: list[str] = None,
        ignore_user_data: list[str] = None,
        ignore_chat_data: list[str] = None,
        ignore_bot_data: list[str] = None,
        ignore_conversations_data: list[str] = None,
        # ignore_callback_data: list[str] = None,
        update_interval: float = 60,
        load_on_flush=True,
    ):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        ignore_general_data = ignore_general_data or []

        ignore_user_data = ignore_user_data or []
        ignore_chat_data = ignore_chat_data or []
        ignore_bot_data = ignore_bot_data or []
        ignore_conversations_data = ignore_conversations_data or []

        self.bot_data: TypeData[BD] = TypeData(
            name_col_bot_data,
            self.db,
            create_col=create_col_if_not_exist,
            to_ignore=ignore_general_data + ignore_bot_data,
        )
        self.chat_data: TypeData[CD] = TypeData(
            name_col_chat_data,
            self.db,
            create_col=create_col_if_not_exist,
            to_ignore=ignore_general_data + ignore_chat_data,
        )
        self.user_data: TypeData[UD] = TypeData(
            name_col_user_data,
            self.db,
            create_col=create_col_if_not_exist,
            to_ignore=ignore_general_data + ignore_user_data,
        )
        # self.callback_data = TypeData(self.name_col_callback_data,self.db, create_col=self.create_col_if_not_exist)
        self.conversations_data: TypeData[_ConvD] = TypeData(
            name_col_conversations_data,
            self.db,
            create_col=create_col_if_not_exist,
            to_ignore=ignore_general_data + ignore_conversations_data,
        )

        self.load_on_flush = load_on_flush

        self.store_data = PersistenceInput(
            self.bot_data.exists(),
            self.chat_data.exists(),
            self.user_data.exists(),
            False,  # self.callback_data.exists()
        )
        super().__init__(
            store_data=self.store_data,
            update_interval=update_interval,
        )

    async def post_init(self):
        if getattr(self, "_inited", False):
            return

        await self.bot_data.post_init()
        await self.chat_data.post_init()
        await self.user_data.post_init()
        await self.conversations_data.post_init()

        self.store_data = PersistenceInput(
            self.bot_data.exists(),
            self.chat_data.exists(),
            self.user_data.exists(),
            False,  # self.callback_data.exists()
        )

        setattr(self, "_inited", True)

    # [==================================== GENERAL FUNCTIONS ====================================]

    async def get_data(self, type_data: TypeData) -> dict:
        await self.post_init()
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
        await self.post_init()
        if not type_data.exists() or not new_data:
            return
        type_data.filter(new_data)
        data = type_data.data
        if data.get(id_) == new_data:
            return
        data[id_] = deepcopy(new_data)
        if self.load_on_flush:
            return
        new_post = {"_id": id_} | new_data
        old_post = await type_data.col.find_one({"_id": id_})
        if not old_post:
            await type_data.col.insert_one(new_post)
            return
        if old_post != new_post:
            await type_data.col.replace_one({"_id": id_}, new_post)

    async def refresh_data(self, type_data: TypeData, id_: int, local_data: NEW_DATA) -> None:
        return await self.update_data(type_data, id_, local_data)

    async def drop_data(self, type_data: TypeData, id_: int) -> None:
        await self.post_init()
        if not type_data.exists():
            return
        data = type_data.data
        if data.get(id_):
            data.pop(id_)
            await type_data.col.delete_one({"_id": id_})

    async def load_all_type_data(self, type_data: TypeData) -> None:
        await self.post_init()
        if not type_data.exists():
            return
        data = type_data.data

        async def gather(key: str, item: dict):
            new_post = {"_id": key} | item
            old_post = await type_data.col.find_one({"_id": key})
            if not old_post:
                await type_data.col.insert_one(new_post)
                return
            if old_post != new_post:
                await type_data.col.replace_one({"_id": key}, new_post)

        await asyncio.gather(*[gather(key, item) for key, item in data.items()])

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
        await self.post_init()
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
        await self.post_init()
        if not self.bot_data.exists() or data == {}:
            return
        old_data = self.bot_data.data
        if old_data == data:
            return
        new_data = deepcopy(data)
        self.bot_data.data = new_data
        if self.load_on_flush:
            return
        collection = self.bot_data.col
        new_post = {"_id": BOT_DATA_KEY, "content": new_data}
        self.bot_data.filter(new_post["content"])
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
        await self.post_init()
        if not self.conversations_data.exists():
            return {}

        def string_to_tuple(string: str) -> tuple[int, int]:
            first, second = map(int, string.replace("(", "").replace(")", "").split(","))
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
        await self.post_init()
        if not self.conversations_data.exists():
            return
        data: dict[str, dict] = self.conversations_data.data
        if data.setdefault(name, {}).get(key) == new_state:
            return
        data[name][key] = new_state
        if self.load_on_flush:
            return
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
        await self.post_init()
        if self.load_on_flush:
            await self.load_all_type_data(self.user_data)
            await self.load_all_type_data(self.chat_data)
            if self.bot_data.exists():
                new_post = {"_id": BOT_DATA_KEY, "content": self.bot_data.data}
                old_post = await self.bot_data.col.find_one({"_id": BOT_DATA_KEY})
                if old_post:
                    if old_post != new_post:
                        await self.bot_data.col.update_one(
                            {"_id": BOT_DATA_KEY}, {"$set": {"content": self.bot_data.data}}
                        )
                else:
                    await self.bot_data.col.insert_one(new_post)
        self.client.close()
