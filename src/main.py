import argparse
import asyncio
import logging
import os

import aiogram
import toml
from loguru import logger

import services
from base import YaMusic, UserRepo
from ents import Track, User

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

# initialise clients
ya_music_client: YaMusic = services.Factory.create_yandex_music(token=config['YANDEXMUSIC']['token'])
yt = services.Factory.create_pytube_client()
dispatcher = aiogram.Dispatcher(bot=aiogram.Bot(token=config['TELEGRAMBOT']['token']), )

# setup db

if config['DATABASE']['disabled']:
    user_repo: UserRepo = services.Factory.create_memory_user_repo()
else:
    user_repo = services.Factory.create_mysql_user_repo(
        host=config['DATABASE']['host'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password'],
        db_name=config['DATABASE']['db_name'],
    )


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
    user = User(id_=msg.from_user.id,
                username=msg.from_user.username,
                full_name=msg.from_user.full_name,
                )
    if not await user_repo.does_exist(user):
        await user_repo.register(user)
    text = '''Привет, отправь мне ссылку ;) 

На данный момент я поддерживаю сервисы:
1) Яндекс Музыка
2) Youtube '''
    await msg.answer(text)


async def process_yandex_track(msg: aiogram.types.Message):
    logger.info(f'process ya track from `{msg.from_user.id}`')
    track = await ya_music_client.extract_track_from_url(msg.text)
    await send_track(track, msg)


async def process_youtube_video(msg: aiogram.types.Message):
    logger.info(f'process yt video from `{msg.from_user.id}`')
    track = await yt.extract_track_from_url(msg.text)
    if 300 < track.duration:
        await msg.answer('Длительность видео не может превышать 5 минут.')
        return
    await send_track(track, msg)


async def process_search_request(msg: aiogram.types.Message):
    logger.info(f'process search request `{msg.text}` from `{msg.from_user.id}`')
    track = await ya_music_client.search_first_track(msg.text)

    if not track:
        await msg.answer('Ничего не удалось найти :(')
        return
    await send_track(track, msg)


# main
async def main():
    # register telegram message handlers
    dispatcher.register_message_handler(process_yandex_track, regexp=r'https://music.yandex.')
    dispatcher.register_message_handler(process_youtube_video,
                                        regexp='https://www.youtube.com/watch|https://youtu.be', )
    dispatcher.register_message_handler(process_start_command, commands=['start', 'help'], state='*')
    dispatcher.register_message_handler(process_search_request, content_types=aiogram.types.ContentType.TEXT)

    # create io tasks
    loop.create_task(dispatcher.start_polling())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
