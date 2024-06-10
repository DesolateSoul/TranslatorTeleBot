from googletrans import Translator
from telebot.async_telebot import AsyncTeleBot
import asyncio
import aiohttp
from telebot import types
from tokens import TG_TOKEN, OCR_APIKEY
from requests import get
import json

bot = AsyncTeleBot(TG_TOKEN, parse_mode=None)


async def get_response(url, params):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


# Обработка команды /start приветствие.
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    await bot.reply_to(message, '------\n'
                       + 'Здравствуй, '
                       + message.from_user.first_name
                       + ' \nПереведу с русского на английский \nИ с других языков на русский '
                       + '\n------')


# Обработка команды /help.
@bot.message_handler(commands=['help'])
async def send_help(message):
    await bot.reply_to(message, '------\n'
                       + 'Просто вводи текст и нажимай отправить\n'
                       + 'Я сам определю какой это язык\n'
                       + 'Если не перевел, попробуй еще раз\n'
                       + 'Перевод google'
                       + '\n------'
                       + '\nДоступные команды:'
                       + '\n/help'
                       + '\n/start'
                       + '\n/dictionary <слово>')


# Обработка команды /dictionary.
@bot.message_handler(commands=['dictionary'])
async def dictionary(message):
    word = message.text.split()[1:][0]
    response = await get_response(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", params={
        "format": "json"})
    await bot.reply_to(message, f'Ищу значение слова "{word}"...')
    word_meaning = f"Вот различные значения слова '{word}':\n" + \
                   '\n'.join([f"\nЧасть речи: {meaning['partOfSpeech']}\nЗначения:\n" + \
                              "\n".join([definition['definition'] for definition in meaning['definitions']]) for meaning
                              in response[0]['meanings']])
    await bot.reply_to(message, word_meaning)


# Обработка текста сообщения, если ввод на русском, то перевод на английский,
# если другой язык, то перевод на русский.
@bot.message_handler()
async def user_text(message):
    translator = Translator()

    # Определение языка ввода.
    lang = translator.detect(message.text)
    lang = lang.lang

    # Если ввод по русски, то перевести на английский по умолчанию.
    if lang == 'ru':
        send = translator.translate(message.text)
        await bot.reply_to(message, '------\n' + send.text + '\n------')

    # Иначе другой язык перевести на русский {dest='ru'}.
    else:
        send = translator.translate(message.text, dest='ru')
        await bot.reply_to(message, '------\n' + send.text + '\n------')


# Обработка картинок с подписями
@bot.message_handler(content_types=['photo'])
async def handle_image(message):
    # Обработчик изображений
    chat_id = message.chat.id

    photo = await bot.get_file(message.photo[-1].file_id)
    photo_url = f'https://api.telegram.org/file/bot{TG_TOKEN}/{photo.file_path}'
    filetype = photo.file_path.split(".")[-1]
    await bot.send_message(chat_id, 'Раcпознавание текста на изображении...')
    response = await get_response(f'https://api.ocr.space/parse/imageurl?', params={
        "apikey": OCR_APIKEY,
        "url": photo_url,
        "filetype": photo.file_path.split(".")[-1]})
    words = response['ParsedResults'][0]['ParsedText']
    await bot.reply_to(message, f'Распознанный текст: {words}')


# Обработка инлайн запросов. Инлайн режим необходимо включить в настройках бота у @BotFather.
@bot.inline_handler(lambda query: True)
async def inline_query(query):
    results = []
    translator = Translator()
    text = query.query.strip()

    # Если запрос пустой, не делаем перевод
    if not text:
        return

    # Определение языка ввода.
    lang = translator.detect(text)
    lang = lang.lang

    # Если ввод по русски, то перевести на английский по умолчанию.
    if lang == 'ru':
        send = translator.translate(text)
        results.append(types.InlineQueryResultArticle(
            id='1', title=send.text, input_message_content=types.InputTextMessageContent(
                message_text=send.text)))

    # Иначе другой язык перевести на русский {dest='ru'}.
    else:
        send = translator.translate(text, dest='ru')
        results.append(types.InlineQueryResultArticle(
            id='1', title=send.text, input_message_content=types.InputTextMessageContent(
                message_text=send.text)))

    await bot.answer_inline_query(query.id, results)


# Запуск и повторение запуска при сбое.
asyncio.run(bot.infinity_polling())
