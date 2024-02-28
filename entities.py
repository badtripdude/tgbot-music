from dataclasses import dataclass


@dataclass()
class Track:
    title: str
    duration: int
    thumb: bytes
    artists: [str]
    audio: bytes
    audio_url: str = None


class TrackV2:
    async def get_title(self) -> str:
        ...

    async def get_duration(self) -> int:
        ...

    async def get_thumb(self) -> bytes:
        ...

    async def get_artists(self) -> list[str]:
        ...

    async def get_audio(self) -> bytes:
        ...

    async def get_audio_url(self) -> str:
        ...


@dataclass
class YtVideo:
    duration: int
    title: str
    author: str
    buffer: bytes
