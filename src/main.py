import argparse
import asyncio
import logging
import os
import sys

import aiocache
import aiogram
import toml
from loguru import logger

sys.path.extend(['../'])

from core.entities import Track, User
from core.services import UserService, YandexMusicServiceWithCache, YouTubeServiceWithCache
from src.infrastructure import repository

parser = argparse.ArgumentParser()
parser.add_argument('-cp', '--config_path', default=r'../data/config.toml', type=str)
parser.add_argument('-lp', '--logs_path', default=r'../data/logs/', type=str)

args = parser.parse_args()

# configure logs
os.makedirs(args.logs_path, exist_ok=True)
logging.basicConfig(filename=args.logs_path + r'logs.log', filemode='w', level=logging.INFO)
logger.add(args.logs_path + r'app.log', mode='w', level=0)

# load config
config = toml.load(args.config_path)

# setup cache
# You can use either classes or strings for referencing classes
aiocache.caches.set_config({
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.PickleSerializer"
        },
        'ttl': 3600

    },
    'redis': {
        'cache': "aiocache.RedisCache",
        'endpoint': config['CACHE']['REDIS']['host'],
        'port': 6379,
        'timeout': config['CACHE']['REDIS']['timeout'],
        'serializer': {
            'class': "aiocache.serializers.PickleSerializer"
        },
        'ttl': config['CACHE']['REDIS']['ttl']
    }
})

# initialise clients
ya_music_client = YandexMusicServiceWithCache(
    repository.Factory.create_yandex_music(token=config['YANDEXMUSIC']['token']))
yt = YouTubeServiceWithCache(repository.Factory.create_pytube_client())
dispatcher = aiogram.Dispatcher(bot=aiogram.Bot(token=config['TELEGRAMBOT']['token']), )

# setup user service

if config['DATABASE']['disabled']:
    user_service = UserService(repository.Factory.create_memory_user_repo())
else:
    user_service = UserService(repository.Factory.create_mysql_user_repo(
        host=config['DATABASE']['host'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password'],
        db_name=config['DATABASE']['db_name'],
    ))


async def send_track(track: Track, msg):
    bot_username = (await msg.bot.me)['username']
    await msg.answer_audio(track.audio, title=track.title,
                           duration=track.duration,
                           caption=f'<a href="https://t.me/{bot_username}">🎵 Сервис.Музыка</a>',
                           thumb=track.thumb,
                           performer=', '.join(track.artists),
                           parse_mode='HTML')


# controllers

async def process_start_command(msg: aiogram.types.Message):
    logger.info(f'process start from user `{msg.from_user}`')
    user = User(telegram_chat_id=msg.from_user.id,
                username=msg.from_user.username,
                full_name=msg.from_user.full_name,
                )
    await user_service.register(user)
    text = '''Привет, отправь мне ссылку или текстовое сообщение для поиска ;) 

На данный момент я поддерживаю сервисы:
1) Яндекс Музыка
2) Youtube 

* поиск по тексту на данный момент производится с помощью сервиса ЯндексМузыка

'''
    await msg.answer(text)


async def process_yandex_track_url(msg: aiogram.types.Message):
    logger.info(f'process ya track from `{msg.from_user}`')
    msg.text = msg.text.rstrip('?utm_medium=copy_link')
    track = await ya_music_client.extract_track_from_url(msg.text)
    await send_track(track, msg)


async def process_youtube_video_url(msg: aiogram.types.Message):
    logger.info(f'process yt video from `{msg.from_user}`')
    track = await yt.extract_track_from_url(msg.text)
    if 300 < track.duration:
        await msg.answer('Длительность видео не может превышать 5 минут.')
        return
    await send_track(track, msg)


async def process_search_request(msg: aiogram.types.Message):
    logger.info(f'process search request `{msg.text}` from `{msg.from_user}`')
    track: [object] = await ya_music_client.search_tracks(text=msg.text, amount=1)

    if not track:
        await msg.answer('Ничего не удалось найти :(')
        return
    await send_track(track[0], msg)


async def process_inline_search(inline_query: aiogram.types.InlineQuery):
    import hashlib
    text = inline_query.query
    logger.info(f'inline query `{text}` by {inline_query.from_user}')
    tracks = await ya_music_client.search_tracks(text, amount=1)
    result_id = hashlib.md5(text.encode()).hexdigest()
    items = [aiogram.types.InlineQueryResultAudio(
        id=result_id,
        audio_url=track.url,
        title=track.title,
        performer=', '.join(track.artists),

    ) for track in tracks]
    await inline_query.bot.answer_inline_query(inline_query.id,
                                               results=items, cache_time=60,
                                               )


# main
async def main():
    # register telegram message handlers
    dispatcher.register_message_handler(process_yandex_track_url, regexp=r'https://music.yandex.')
    dispatcher.register_message_handler(process_youtube_video_url,
                                        regexp='https://www.youtube.com/watch|https://youtu.be', )
    dispatcher.register_message_handler(process_start_command, commands=['start', 'help'], state='*')
    dispatcher.register_message_handler(process_search_request, content_types=aiogram.types.ContentType.TEXT)

    dispatcher.register_inline_handler(process_inline_search, lambda q: q.query)
    # create io tasks
    loop.create_task(dispatcher.start_polling())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
