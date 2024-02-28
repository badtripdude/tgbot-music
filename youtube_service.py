import abc
import io

import pytube
import requests

from entities import YtVideo, TrackV2


class PytubeYtTrack(TrackV2):
    def __init__(self, yt_object):
        self.yt_object = yt_object
        # self.audio_stream = self.yt_object.streams.filter(file_extension='mp3').last() # .get_audio_only()
        self.audio_stream = yt_object.streams.get_audio_only()
        self.title = self.yt_object.title
        self.duration = self.yt_object.length
        self.artists = [self.yt_object.author]

    async def get_thumb(self) -> bytes:
        return requests.get(self.yt_object.thumbnail_url).content

    async def get_audio(self):
        from io import BytesIO
        buffer = BytesIO()
        self.audio_stream.stream_to_buffer(buffer)
        buffer.seek(0)
        return buffer.read()

    async def get_title(self) -> str:
        return self.title

    async def get_duration(self) -> int:
        return self.duration

    async def get_artists(self) -> list[str]:
        return self.artists

    async def get_audio_url(self) -> str:
        return self.audio_stream.url


class PytubeYtVideo(YtVideo):
    def __init__(self, yt_object: pytube.YouTube, yt_stream: pytube.Stream):
        self.yt_object = yt_object
        self.yt_stream = yt_stream
        self.title = self.yt_object.title
        self.duration = yt_object.length
        self.artists = [self.yt_object.author]

    @property
    def track(self):
        return PytubeYtTrack(self.yt_object)

    @property
    def buffer(self):
        buffer = io.BytesIO()
        self.yt_stream.stream_to_buffer(buffer)
        buffer.seek(0)
        return buffer.read()


class YouTubeService(abc.ABC):
    @abc.abstractmethod
    async def extract_yt_video_from_url(self, url) -> YtVideo:
        ...

    @abc.abstractmethod
    async def extract_track_from_url(self, url) -> TrackV2:
        ...

    @abc.abstractmethod
    async def search_tracks(self, query: str, amount: int = 1) -> list[TrackV2]:
        ...

    @abc.abstractmethod
    async def search_video(self, query: str, amount: int = 1) -> list[YtVideo]:
        ...


class PyTubeService(YouTubeService):

    async def extract_yt_video_from_url(self, url) -> YtVideo:
        yt = pytube.YouTube(use_oauth=True, url=url)
        return PytubeYtVideo(yt, yt.streams.filter(progressive=True, file_extension='mp4').order_by(
            'resolution').desc().first())

    async def search_video(self, query: str, amount: int = 1) -> list[YtVideo]:
        from pytube import Search
        res = Search(query).results
        stream = res[0].streams.filter(progressive=True, file_extension='mp4').order_by(
            'resolution').desc().first()
        return [PytubeYtVideo(res[0], stream)]

    async def extract_track_from_url(self, url) -> TrackV2:
        yt = pytube.YouTube(url)
        return PytubeYtTrack(yt)

    async def search_tracks(self, query: str, amount: int = 1) -> list[TrackV2]:
        from pytube import Search
        res = Search(query).results[:amount]

        return [PytubeYtTrack(t) for t in res]
