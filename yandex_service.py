import abc
import asyncio
import re

import yandex_music

from entities import Track, TrackV2


class YandexMusicService(abc.ABC):
    @abc.abstractmethod
    async def search_tracks(self, text: str, amount: int = 1) -> list[TrackV2]:
        ...

    @abc.abstractmethod
    async def extract_track_from_url(self, url: str) -> TrackV2:
        ...


class YAMTrack(TrackV2):
    def __init__(self, track: yandex_music.Track):
        self.track = track
        self.title = track.title
        self.duration = track.duration_ms // 1000
        self.artists = track.artists_name()

    async def get_audio_url(self):
        return (await self.track.get_download_info_async(get_direct_links=True))[0].direct_link

    async def get_audio(self, **kwargs):
        return await self.track.download_bytes_async(bitrate_in_kbps=320)

    async def get_title(self) -> str:
        return self.title

    async def get_thumb(self) -> bytes:
        return await self.track.download_og_image_bytes_async()

    async def get_duration(self) -> int:
        return self.duration

    async def get_artists(self) -> list[str]:
        return self.artists


class YandexService(YandexMusicService):
    def __init__(self, token):
        import yandex_music
        self.client = yandex_music.ClientAsync(token=token)
        asyncio.get_event_loop().create_task(self._init())

    async def _init(self):
        await self.client.init()

    async def search_tracks(self, text: str, amount: int = 1) -> list[TrackV2]:
        res = await self.client.search(text=text, type_='track', )
        if not res or not res.tracks:
            return []
        tracks = res.tracks.results[:amount]

        return [
            YAMTrack(track)
            for track in tracks
        ]

    async def extract_track_from_url(self, url) -> TrackV2:
        track, *_ = await self.client.tracks([self.extract_track_id(url)])
        track: yandex_music.Track
        return YAMTrack(track)

    @staticmethod
    def extract_track_id(url: str):
        res, = re.findall(r'album/(\d+)/track/(\d+)', url)
        return f'{res[1]}:{res[0]}'
