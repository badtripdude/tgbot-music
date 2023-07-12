from __future__ import annotations

import asyncio
import re

import pytube
import requests
import yandex_music

from base import YaMusic, Yt, UserRepo
from ents import Track, User


class Factory:
    @staticmethod
    def create_yandex_music(token: str) -> YaMusic:
        return YandexMusic(token=token)

    @staticmethod
    def create_pytube_client() -> Yt:
        return PytubeYt()

    @staticmethod
    def create_memory_user_repo() -> UserRepo:
        return MemoryUserRepo()

    @staticmethod
    def create_mysql_user_repo(host: str, user: str, password: str, db_name: str) -> MysqlUserRepo:
        return MysqlUserRepo(host, user, password, db_name)


class YandexMusic(YaMusic):
    def __init__(self, token):
        import yandex_music
        self.client = yandex_music.ClientAsync(token=token)
        asyncio.get_event_loop().create_task(self._init())

    async def _init(self):
        await self.client.init()

    async def search_first_track(self, text: str) -> Track | None:
        res = await self.client.search(text=text,
                                       type_='track')
        if not res or not res.tracks:
            return
        first_track, *_ = res.tracks.results
        first_track: yandex_music.Track

        return Track(first_track.title, first_track.duration_ms // 1000,
                     (await first_track.download_og_image_bytes_async()),
                     first_track.artists_name(),
                     audio=(await first_track.download_bytes_async()))

    async def extract_track_from_url(self, url: str) -> Track:
        track, *_ = await self.client.tracks([self.extract_track_id(url)])
        track: yandex_music.Track
        return Track(track.title, track.duration_ms // 1000,
                     thumb=(await track.download_og_image_bytes_async()),
                     artists=track.artists_name(),
                     audio=(await track.download_bytes_async()))

    @staticmethod
    def extract_track_id(url: str):
        res, = re.findall(r'album/(\d+)/track/(\d+)', url)
        return f'{res[1]}:{res[0]}'


class PytubeYt(Yt):
    async def extract_track_from_url(self, url: str) -> Track:
        yt = pytube.YouTube(url, allow_oauth_cache=True, )
        audio = yt.streams.get_audio_only()

        from io import BytesIO
        buffer = BytesIO()
        audio.stream_to_buffer(buffer)
        buffer.seek(0)

        thumb = requests.get(yt.thumbnail_url).content
        return Track(audio.title, yt.length, thumb, [yt.author], buffer.read())


class MemoryUserRepo(UserRepo):
    def __init__(self):
        self.lst = []

    async def register(self, user: User):
        self.lst.append(user.id_)

    async def does_exist(self, user: User) -> bool:
        return user.id_ in self.lst


class MysqlUserRepo(UserRepo):
    def __init__(self, host: str, user: str, password: str,
                 db_name: str):
        import db
        self.conn = db.MysqlConnection
        self.conn.MYSQL_INFO = {
            'host': host,
            'user': user,
            'password': password,
            'db': db_name,
        }

    async def register(self, user: User):
        sql = 'INSERT INTO `users` (`chat_id`, `full_name`, `username`) VALUES (%s, %s, %s)'
        params = (user.id_, user.full_name, user.username)
        await self.conn._make_request(sql, params)

    async def does_exist(self, user: User):
        sql = 'SELECT * FROM `users` WHERE `chat_id` = %s'
        params = (user.id_,)
        r = await self.conn._make_request(sql, params, fetch=True)
        return bool(r)

    '''
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `chat_id` int NOT NULL,
  `full_name` varchar(90) DEFAULT NULL,
  `username` varchar(90) DEFAULT NULL,
  `date` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_UNIQUE` (`id`),
  UNIQUE KEY `chat_id_UNIQUE` (`chat_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    '''
