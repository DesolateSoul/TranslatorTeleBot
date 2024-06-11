from googletrans import Translator
from telebot.async_telebot import AsyncTeleBot
import asyncio
import aiohttp
from tokens import TG_TOKEN, OCR_APIKEY
from random import choice
import requests
from bs4 import BeautifulSoup


bot = AsyncTeleBot(TG_TOKEN, parse_mode=None)


async def get_response(url, params):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


# Обработка команды /help.
@bot.message_handler(commands=['help'])
async def send_help(message):
    await bot.reply_to(message, '------\n'
                       + 'Просто отправь текст или картинку для распознавания текста\n'
                       + 'Текст переводится с русского на английский,'
                       + ' с других языков на русский\n'
                       + 'Распознавание текста OCR\n'
                       + 'Перевод google'
                       + '\n------'
                       + '\nДоступные команды:'
                       + '\n/help'
                       + '\n/dictionary <слово>'
                       + '\n/what_to_read')


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


# Обработка команды /what_to_read.
@bot.message_handler(commands=['what_to_read'])
async def scrap_html(message):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/58.0.3029.110 Safari/537.36"}
    response = requests.get('https://en.wikipedia.org/wiki/List_of_novels_based_on_comics', headers=headers)

    # Инициализируем списки данных для хранения полученной скрейпингом информации
    titles = []
    authors = []
    publishers = []
    release_dates = []

    # Проверяем валидность полученного ответа
    if response.status_code == 200:

        # Парсим HTML при помощи Beautiful Soup
        soup = BeautifulSoup(response.text, 'html.parser')

        # CSS-селектор для основных таблиц
        table = soup.find('table', {'class': 'wikitable'})

        # Обходим строки в цикле, пропуская заголовок
        for row in table.find_all('tr')[1:]:
            # Извлекаем данные каждого столбца при помощи CSS-селекторов
            columns = row.find_all(['td', 'th'])

            title = columns[0].text.strip()
            author = columns[1].text.strip()
            publisher = columns[2].text.strip()
            release_date = columns[4].text.strip()

            titles.append(title)
            authors.append(author)
            publishers.append(publisher)
            release_dates.append(release_date)

    random_book_number = choice([x for x in range(len(titles))])

    await bot.reply_to(message, f'''Название: {titles[random_book_number]}\nАвтор: {authors[random_book_number]}
Дата выхода: {release_dates[random_book_number]}''')


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


# Обработка картинок
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


# Запуск и повторение запуска при сбое.
asyncio.run(bot.infinity_polling())
