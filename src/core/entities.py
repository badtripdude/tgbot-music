from dataclasses import dataclass


@dataclass()
class Track:
    title: str
    duration: int
    thumb: bytes
    artists: [str]
    audio: bytes


@dataclass()
class User:
    id_: int = None
    username: str = None
    full_name: str = None
    telegram_chat_id: int = None
