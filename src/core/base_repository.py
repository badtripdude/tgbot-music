from __future__ import annotations

import abc

from .entities import Track, User


class YandexMusic(abc.ABC):
    @abc.abstractmethod
    async def search_first_track(self, text: str) -> Track | None:
        ...

    @abc.abstractmethod
    async def extract_track_from_url(self, url: str) -> Track:
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
