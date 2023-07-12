from __future__ import annotations

import abc

from src.ents import Track


class YaMusic(abc.ABC):
    @abc.abstractmethod
    async def search_first_track(self, text: str) -> Track | None:
        ...

    @abc.abstractmethod
    async def extract_track_from_url(self, url: str) -> Track:
        ...


class Yt(abc.ABC):
    @abc.abstractmethod
    async def extract_track_from_url(self, url: str) -> Track:
        ...


class UserRepo(abc.ABC):
    @abc.abstractmethod
    async def register(self, user):
        ...

    @abc.abstractmethod
    async def does_exist(self, by) -> bool:
        ...
