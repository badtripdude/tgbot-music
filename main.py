import enum
import html
import json
import logging
import traceback
from os import getenv
from uuid import uuid4

from loguru import logger
from telegram import InlineQueryResultAudio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, \
    filters, ConversationHandler, InlineQueryHandler

from db import DatabaseManager
from entities import TrackV2
from yandex_service import YandexMusicService, YandexService
from youtube_service import YouTubeService, PyTubeService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename='telegram.log', level=logging.DEBUG, filemode='w'
)


class SpecificLoggerFilter(logging.Filter):
    def __init__(self, name=""):
        super().__init__(name)
        self.name = name

    def filter(self, record):
        return record.name == self.name


specific_name = "telegram.ext.Application"

for handler in logging.getLogger().handlers:
    handler.addFilter(SpecificLoggerFilter(specific_name))

logger.add(r"app.log", enqueue=True, level='DEBUG')
DEVELOPER_CHAT_ID = getenv('DEVELOPER_CHAT_ID', None) or input('Please enter your telegram chat id(or Enter): ')
YANDEX_TOKEN = getenv('YANDEX_TOKEN', None) or input('Please enter your yandex token(or Enter): ')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN', None) or input('Please enter your telegram token: ')


class Conv(enum.Enum):
    CHOOSING = enum.auto()
    LIST_SERVICES = enum.auto()


yt_obj: YouTubeService = PyTubeService()
yam: YandexMusicService = YandexService(token=YANDEX_TOKEN)
db = DatabaseManager('db.db')


async def send_track(track: TrackV2, update, context):
    bot_username = (await context.bot.get_me()).username
    await context.bot.send_audio(chat_id=update.effective_chat.id,
                                 audio=await track.get_audio(), title=await track.get_title(),
                                 duration=await track.get_duration(),
                                 caption=f'<a href="https://t.me/{bot_username}">🎵 Сервис.Музыка</a>',
                                 thumbnail=await track.get_thumb(),
                                 performer=', '.join(await track.get_artists()),
                                 parse_mode='HTML')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.user_exists(update.effective_user.id):
        db.add_user(update.effective_user.id, update.effective_user.username, update.effective_user.first_name,
                    update.effective_user.last_name)
    context.user_data.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text='''Привет, отправь мне ссылку или текстовое сообщение для поиска ;) 

На данный момент я поддерживаю сервисы:
1) Яндекс Музыка
2) Youtube''')
    return ConversationHandler.END


async def yandex_track_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    link = msg.text.rstrip('?utm_medium=copy_link')
    track = await yam.extract_track_from_url(link)
    await send_track(track, update, context)


async def send_youtube_choose(update, context):
    b1 = InlineKeyboardButton('Видео', callback_data='yt_video')
    b2 = InlineKeyboardButton('Аудио', callback_data='yt_audio')
    b3 = InlineKeyboardButton('<-', callback_data='back')
    ikm = InlineKeyboardMarkup([[b1, b2],
                                [b3]])
    await context.bot.send_message(update.effective_chat.id, 'Что извлекаем?', reply_markup=ikm)
    return Conv.CHOOSING


async def youtube_track_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        context.user_data.update({'url': msg.text})
        return await send_youtube_choose(update, context)

    except:
        await context.bot.send_message(update.effective_chat.id, 'Произошла видимо какая-то ошибка...')


async def youtube_choosing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.delete_message()
    try:
        if 'url' in context.user_data:
            if query.data == 'yt_video':
                video = await yt_obj.extract_yt_video_from_url(
                    context.user_data.get('url', r'https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
                if video.duration > 601:
                    await context.bot.send_message(update.effective_chat.id,
                                                   r'Длина видео должна быть короче 10 минут')
                else:
                    await context.bot.send_video(update.effective_chat.id, video.buffer)

            if query.data == 'yt_audio':
                track = await yt_obj.extract_track_from_url(
                    context.user_data.get('url', r'https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
                if await track.get_duration() > 601:
                    await context.bot.send_message(update.effective_chat.id,
                                                   r'Длина видео должна быть короче 10 минут')
                else:
                    await send_track(
                        track,
                        update, context)

            context.user_data.pop('url')

        if 'query' in context.user_data:
            if query.data == 'yt_video':
                video, = await yt_obj.search_video(context.user_data.get('query', 'rickroll'))
                if video.duration > 601:
                    await context.bot.send_message(update.effective_chat.id,
                                                   r'Длина видео должна быть короче 10 минут')
                else:
                    await context.bot.send_video(update.effective_chat.id, video.buffer)

            if query.data == 'yt_audio':
                track = (await yt_obj.search_tracks(context.user_data.get('query', 'rickroll')))[0]
                if await track.get_duration() > 601:
                    await context.bot.send_message(update.effective_chat.id,
                                                   r'Длина видео должна быть короче 10 минут')
                else:
                    await send_track(track,
                                     update, context)

            context.user_data.pop('query')
    except Exception as e:
        await context.bot.send_message(update.effective_chat.id, 'Что-то пошло не так...')
        raise e
    return ConversationHandler.END


async def search_track_by_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data.update({'query': text})
    b1 = InlineKeyboardButton('Youtube', callback_data='yt')
    b2 = InlineKeyboardButton('YandexMusic', callback_data='yam')
    b3 = InlineKeyboardButton('<-', callback_data='stop')
    ikm = InlineKeyboardMarkup([[b1, b2],
                                [b3]])
    await context.bot.send_message(update.effective_chat.id, 'Где искать?', reply_markup=ikm)
    return Conv.LIST_SERVICES


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == 'stop':
        await query.delete_message()
        return ConversationHandler.END
    if query.data == 'yt':
        await query.edit_message_text('ищем в Youtube...')
        return await send_youtube_choose(update, context)
    if query.data == 'yam':
        await query.edit_message_text('ищем в YandexMusic...')
        await send_track((await yam.search_tracks(context.user_data.get('query', 'rickroll'), 1))[0],
                         update, context)
        return ConversationHandler.END


async def inline_mod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    tracks = await yam.search_tracks(query, amount=3)
    if not tracks:
        return

    results = [
        InlineQueryResultAudio(str(uuid4()),
                               title=await t.get_title(),
                               audio_url=await t.get_audio_url(),
                               audio_duration=await t.get_duration(),
                               performer=', '.join(await t.get_artists()),
                               ) for t in tracks
    ]
    await update.inline_query.answer(results, cache_time=3)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    if DEVELOPER_CHAT_ID:
        await context.bot.send_message(
            chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML
        )


if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(InlineQueryHandler(inline_mod, block=True))
    conv = ConversationHandler(entry_points=[
        CommandHandler('start', start),
        MessageHandler(
            filters.Regex(
                pattern='https://www.youtube.com/watch|'
                        'https://youtu.be|'
                        'https://www.youtube.com/shorts|'
                        'https://youtube.com/shorts'
            ), youtube_track_url),
        MessageHandler(
            filters.TEXT,
            search_track_by_query, ),
        application.add_handler(
            MessageHandler(
                filters.Regex(
                    pattern='https://music.yandex.'
                ),
                yandex_track_url
            ))
    ],
        states={Conv.CHOOSING: [CallbackQueryHandler(youtube_choosing)],
                Conv.LIST_SERVICES: [CallbackQueryHandler(list_services)]},
        fallbacks=[CommandHandler('start', start)],
        per_message=False)
    application.add_handler(conv)
    application.run_polling()
