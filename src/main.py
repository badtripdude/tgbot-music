import asyncio
import re
import aiogram
import toml
import yandex_music
from loguru import logger
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-cp', '--config_path', default=r'..\data\config.toml', type=str)

args = parser.parse_args()

# configure logs
logging.basicConfig(filename=r'..\data\logs\logs.log', filemode='w', level=logging.INFO)
logger.add(r'..\data\logs\app.log', mode='a', level=0)

config = toml.load(args.config_path)

# initialise clients
ya_music_client = yandex_music.ClientAsync(token=config['YANDEXMUSIC']['token'])
dispatcher = aiogram.Dispatcher(bot=aiogram.Bot(token=config['TELEGRAMBOT']['token']))


async def process_start_command(msg: aiogram.types.Message):
    text = '''Привет, отправь мне ссылку из сервиса ЯдексМузыка на трек ;)'''
    await msg.answer(text)


async def process_yandex_track(msg: aiogram.types.Message):
    def extract_track_id(url: str):
        res, = re.findall(r'album/(\d+)/track/(\d+)', url)
        return f'{res[1]}:{res[0]}'

    logger.info(f'process new track by `{msg.from_user.id}`')
    track, *_ = await ya_music_client.tracks([extract_track_id(msg.text)])
    audio_bytes = await track.download_bytes_async()
    bot_username = (await dispatcher.bot.me)['username']
    await msg.answer_audio(
        audio_bytes,
        caption=f'<a href="https://t.me/{bot_username}">🎵 Сервис.Музыка</a>',
        parse_mode='HTML',
        title=f'{track.title}{"" if not track.version else f" ({track.version})"}',
        performer=f'{", ".join(track.artists_name())}',
        thumb=(await track.download_og_image_bytes_async()),
    )


async def main():
    # initialise yandex client
    await ya_music_client.init()

    # register telegram message handlers
    dispatcher.register_message_handler(process_yandex_track, regexp=r'https://music.yandex.')
    dispatcher.register_message_handler(process_start_command, commands=['start', 'help'], state='*')

    # create io tasks
    loop.create_task(dispatcher.start_polling())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
