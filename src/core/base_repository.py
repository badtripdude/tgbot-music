from __future__ import annotations

import abc

from .entities import Track, User


class YandexMusic(abc.ABC):

    @abc.abstractmethod
    async def extract_track_from_url(self, url: str) -> Track:
        ...

    @abc.abstractmethod
    async def search_tracks(self, text: str, amount: int = 5):
        ...


class Youtube(abc.ABC):
    @abc.abstractmethod
    async def extract_track_from_url(self, url: str) -> Track:
        ...


class UserRepo(abc.ABC):
    @abc.abstractmethod
    async def add_user(self, user: User):
        ...

    @abc.abstractmethod
    async def get_by_id(self, id_: int) -> User: ...
