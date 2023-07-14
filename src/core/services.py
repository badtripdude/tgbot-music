from __future__ import annotations

from src.core.base_repository import Youtube, YandexMusic, UserRepo
from src.core.entities import Track, User


class YouTubeService:
    def __init__(self, yt_repo: Youtube):
        self.yt_repo = yt_repo

    async def extract_track_from_url(self, url: str) -> Track:
        track = await self.yt_repo.extract_track_from_url(url)
        return track


class YandexMusicService:
    def __init__(self, yandex_repo: YandexMusic):
        self.yandex_repo = yandex_repo

    async def extract_track_from_url(self, url: str):
        return await self.yandex_repo.extract_track_from_url(url)

    async def search_first_track(self, text: str) -> Track | None:
        return await self.yandex_repo.search_first_track(text)


class UserService:
    def __init__(self, users_repo: UserRepo):
        self.user_repo = users_repo

    async def register(self, user: User):
        if not await self.does_exist(user_id=user.id_):
            await self.user_repo.add_user(user)

    async def does_exist(self, user_id: User.id_) -> bool:
        try:
            if await self.user_repo.get_by_id(user_id):
                return True
        except Exception:
            return False
