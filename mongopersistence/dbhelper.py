import logging
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import CollectionInvalid
from telegram.ext import PersistenceInput

# noinspection PyProtectedMember
from telegram.ext._utils.types import ConversationDict

logger = logging.getLogger(__name__)

D = TypeVar("D", bound=dict)
_BD = TypeVar("_BD")
_CD = TypeVar("_CD")
_UD = TypeVar("_UD")
_ConvD = TypeVar("_ConvD", bound=ConversationDict)


@dataclass
class TypeData(Generic[D]):
    collection_name: str
    db: AsyncIOMotorDatabase

    col: AsyncIOMotorCollection = None
    data: dict = field(default_factory=dict)

    create_col: bool = False

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
            self.col = await self.db.get_collection(self.collection_name)
        self._exist = True


@dataclass
class DBMongoHelper(Generic[_BD, _CD, _UD, _ConvD]):
    # TODO: add support for callback_data

    mongo_url: str
    db_name: str

    name_col_user_data: str | None = None
    name_col_chat_data: str | None = None
    name_col_bot_data: str | None = None

    # name_col_callback_data: str | None = None
    name_col_conversations_data: str | None = None

    create_col_if_not_exist: bool = False

    # TODO: add a feature that allows you to ignore dictionary elements using string
    #  lists so they don't become persistent

    def __post_init__(self) -> None:
        self.client = AsyncIOMotorClient(self.mongo_url)
        self.db = self.client[self.db_name]

        self.bot_data: TypeData[_BD] = TypeData(
            self.name_col_bot_data, self.db, create_col=self.create_col_if_not_exist
        )
        self.chat_data: TypeData[_CD] = TypeData(
            self.name_col_chat_data, self.db, create_col=self.create_col_if_not_exist
        )
        self.user_data: TypeData[_UD] = TypeData(
            self.name_col_user_data, self.db, create_col=self.create_col_if_not_exist
        )
        # self.callback_data = TypeData(self.name_col_callback_data,self.db, create_col=self.create_col_if_not_exist)
        self.conversations_data: TypeData[_ConvD] = TypeData(
            self.name_col_conversations_data, self.db, create_col=self.create_col_if_not_exist
        )

        self.store_data = PersistenceInput(
            self.bot_data.exists(),
            self.chat_data.exists(),
            self.user_data.exists(),
            False,  # self.callback_data.exists()
        )

    async def post_init(self):
        if getattr(self, "_inited", False):
            return

        await self.bot_data.post_init()
        await self.chat_data.post_init()
        await self.user_data.post_init()
        await self.conversations_data.post_init()
        setattr(self, "_inited", True)
