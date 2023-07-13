#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ssl
import os
from aiohttp import web
import telebot
import logging
import requests
import json
import re

from iceberg import (
    mrm_support_redirect,
    bot_start,
    contact,
    mrm_support_receive_photo,
    mrm_support_text,
    mrm_support_bot_button_handler,
    escape_characters
)
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting")

clientPath_prod = [
    'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
    'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
    'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
    ]

clientPath_test = [
    'http://10.2.4.141/Test_MSK_MRM/ws/Telegram.1cws?wsdl',
    'http://10.2.4.141/Test_Piter_MRM/ws/Telegram.1cws?wsdl'
    ]

DATA_PATH_PROD = 'data/'
DATA_PATH_TEST = 'data/test/'

# BID_ROW_WIDTH = 3

WEBHOOK_HOST = os.environ.get('WEBHOOK_HOST', '')
WEBHOOK_PORT = os.environ.get('WEBHOOK_PORT', '')  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr
WEBHOOK_SSL_CERT = 'webhook_cert.pem'
WEBHOOK_SSL_PRIV = 'webhook_pkey.pem'

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

# Set the inline query timeout to 60 seconds
try:
    telebot.apihelper.SEARCH_INLINE_TIMEOUT = 60
except telebot.apihelper.ApiTelegramBotException as e:
    logger.error(e)

async def call_test(request):
    logger.info("test")
    content = "get ok"
    return web.Response(text=content, content_type="text/html")


def default_bot_init(bot_token_env):
    API_TOKEN = os.environ.get(bot_token_env, '')
    bot = telebot.TeleBot(API_TOKEN)

    WEBHOOK_URL_BASE = "https://{}:{}".format(
            os.environ.get('WEBHOOK_HOST', ''), 
            os.environ.get('WEBHOOK_PORT', '')
            )
    WEBHOOK_URL_PATH = "/{}/".format(API_TOKEN)

    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot.remove_webhook()

    # Set webhook
    wh_res = bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,certificate=open(WEBHOOK_SSL_CERT, 'r'))
    print(bot_token_env, 'webhook set', wh_res)
    # print(WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)

    return bot


# Process webhook calls
async def handle(request):
    for bot in bots:
        if request.match_info.get('token') == bot.token:
            request_body_dict = await request.json()
            update = telebot.types.Update.de_json(request_body_dict)
            bot.process_new_updates([update])                        
            return web.Response()

    return web.Response(status=403)


bots	= []

# === === === partners_iceberg_bot ++
partners_iceberg_bot = default_bot_init('PARTNERS_ICEBERG_BOT')
bots.append(partners_iceberg_bot)


@partners_iceberg_bot.message_handler(commands=['start'])
def partners_iceberg_bot_start(message):
    bot_start(message, partners_iceberg_bot, logger)


@partners_iceberg_bot.message_handler(content_types=['contact']) 
def partners_iceberg_bot_contact(message):
     contact(message, partners_iceberg_bot, logger, clientPath_prod, 'partners_iceberg_bot')
# === === === partners_iceberg_bot --


# === === === mrminfobot ++
mrminfobot = default_bot_init('MRMINFOBOT_TOKEN')
bots.append(mrminfobot)

# photo, redirect
@mrminfobot.message_handler(func=lambda message: True, content_types = ['text', 'photo', 'video', 'document', 'audio', 'voice', 'location', 'contact', 'sticker'])
def mrminfobot_message_handler(message):
    logger.info("mrminfobot message_handler: "+str(message.from_user))
    mrm_support_redirect(message, mrminfobot, logger, clientPath_prod)
# === === === mrminfobot --


# === === === mrminfotestbot ++
mrminfotestbot = default_bot_init('MRMINFOTESTBOT_TOKEN')
bots.append(mrminfotestbot)

# Any message, including text, photo, video, etc.
@mrminfotestbot.message_handler(func=lambda message: True, content_types = ['text', 'photo', 'video', 'document', 'audio', 'voice', 'location', 'contact', 'sticker'])
def mrminfotestbot_message_handler(message):
    logger.info("mrminfotestbot message_handler: "+str(message.from_user))
    mrm_support_redirect(message, mrminfotestbot, logger, clientPath_test)
# # === === === mrminfotestbot --


# === === === mrmsupport_bot ++
mrmsupport_bot = default_bot_init('MRMSUPPORTBOT_TOKEN')
bots.append(mrmsupport_bot)


@mrmsupport_bot.message_handler(commands=['start'])
def mrmsupport_bot_start(message):
    bot_start(message, mrmsupport_bot, logger)


@mrmsupport_bot.message_handler(content_types=['contact'])
def mrmsupport_bot_contact(message):
    contact(message, mrmsupport_bot, logger, clientPath_prod, 'mrmsupport_bot')


# Receive compressed and uncompressed photos from user
@mrmsupport_bot.message_handler(content_types=['photo', 'document'])
def mrmsupport_bot_photo(message):
    mrm_support_receive_photo(message, mrmsupport_bot, logger, DATA_PATH_PROD)


@mrmsupport_bot.message_handler(func=lambda message: True, content_types=['text'])
def mrmsupport_bot_text(message):
    mrm_support_text(
        message = message,
        bot = mrmsupport_bot,
        logger = logger,
        data_path = DATA_PATH_PROD,
        clientPath = clientPath_prod,
        row_width = 3,
        max_buttons_per_page = 14
        )                                                                   


@mrmsupport_bot.callback_query_handler(func=lambda call: True)
def mrmsupport_bot_button(call):
    mrm_support_bot_button_handler(
        call = call,
        bot = mrmsupport_bot,
        logger = logger,
        data_path = DATA_PATH_PROD,
        row_width = 3,
        max_buttons_per_page = 14
        )
# === === === mrmsupport_bot --


# === === === mrmsupport_bot_test ++
mrmsupport_bot_test = default_bot_init('MRMSUPPORTBOT_TEST_TOKEN')
bots.append(mrmsupport_bot_test)


@mrmsupport_bot_test.message_handler(commands=['start'])
def mrmsupport_bot_test_start(message):
    bot_start(message, mrmsupport_bot_test, logger)


@mrmsupport_bot_test.message_handler(content_types=['contact'])
def mrmsupport_bot_test_contact(message):
    contact(message, mrmsupport_bot_test, logger, clientPath_test, 'mrmsupport_bot')


# Receive compressed and uncompressed photos from user
@mrmsupport_bot_test.message_handler(content_types=['photo', 'document'])
def mrmsupport_bot_test_photo(message):
    mrm_support_receive_photo(message, mrmsupport_bot_test, logger, DATA_PATH_TEST)


@mrmsupport_bot_test.message_handler(func=lambda message: True, content_types=['text'])
def mrmsupport_bot_test_text(message):
    mrm_support_text(
        message = message,
        bot = mrmsupport_bot_test,
        logger = logger,
        data_path = DATA_PATH_TEST,
        clientPath = clientPath_test,
        row_width = 3,
        max_buttons_per_page = 14
        )


@mrmsupport_bot_test.callback_query_handler(func=lambda call: True)
def mrmsupport_bot_test_button(call):
    mrm_support_bot_button_handler(
        call = call,
        bot = mrmsupport_bot_test,
        logger = logger,
        data_path = DATA_PATH_TEST,
        row_width = 3,
        max_buttons_per_page = 14
        )
# === === === mrmsupport_bot_test --


# === === === gpticebot ++
gpticebot = default_bot_init('GPTICEBOT_TOKEN')
bots.append(gpticebot)


@gpticebot.message_handler(commands=['reset'])
def echo_message(message):
    url = 'http://localhost:'+os.environ.get('GPTICEBOT_PORT')+'/reset_prompt'
    data = {"user_id": message.from_user.id}
    request_str = json.dumps(data)
    content = requests.post(url, json=request_str)
    gpticebot.reply_to(message, content.text, parse_mode="MarkdownV2")


@gpticebot.message_handler(commands=['last_message'])
def last_message(message):
    url = 'http://localhost:'+os.environ.get('GPTICEBOT_PORT')+'/last_message'
    data = {"user_id": message.from_user.id}
    request_str = json.dumps(data)
    content = requests.post(url, json=request_str)
    gpticebot.reply_to(message, content.text, parse_mode="MarkdownV2")


@gpticebot.message_handler(commands=['start'])
def echo_message(message):
    reply_text = """Приветствую, Я GPT-3 робот.
Вы можете задавать мне любые вопросы, но помните, данные которые вы отправляете мне, однажды могут стать публичными.
Чтобы начать диалог заново, используйте команду /reset. Пожалуйста, не забывайте использовать эту команду, поскольку длительные диалоги требуют значительных вычислительных ресурсов."""
    gpticebot.reply_to(message, escape_characters(reply_text), parse_mode="MarkdownV2")
    return


@gpticebot.message_handler(commands=['add'])
def echo_message(message):
    user_id = message.from_user.id
    # Add new user. cmd in format: /add 123456789
    if message.text.startswith('/add'):
        url = 'http://localhost:' + \
            os.environ.get('GPTICEBOT_PORT')+'/user_add'
        new_user_id = message.text.split()[1]
        new_user_name = message.text.split()[2]
        data = {
            "user_id": user_id,
            "new_user_id": new_user_id,
            "new_user_name": new_user_name
        }
        request_str = json.dumps(data)
        content = requests.post(url, json=request_str)
        gpticebot.reply_to(message, escape_characters(content.text), parse_mode="MarkdownV2")
        return
    
@gpticebot.message_handler(commands=['fin'])
def echo_message(message):
    user_id = message.from_user.id
    # Financial report. cmd for 10 days in format: /fin 10
    if message.text.startswith('/fin'):
        url = 'http://localhost:' + \
            os.environ.get('GPTICEBOT_PORT')+'/financial_report'
        
        # extract number using regular expressions
        match = re.search(r'\d+', message.text)
        if match:
            count_of_days = int(match.group())
        else:
            count_of_days = 0
        if message.text == '/fin':
            count_of_days = 0
        data = {
            "user_id": user_id,
            "count_of_days": count_of_days
        }
        request_str = json.dumps(data)
        content = requests.post(url, json=request_str)
        # Check type, if response is text
        if content.headers['content-type'] == 'text/html; charset=utf-8':
            gpticebot.reply_to(message, content.text, parse_mode="MarkdownV2")
        elif content.headers['content-type'] == 'image/png':
            gpticebot.send_photo(message.chat.id, content.content)
        return


@gpticebot.message_handler(func=lambda message: True, content_types=['text'])
def send_user(message):
    try:
        user_id = message.from_user.id
        # Receive user's prompt
        url = 'http://localhost:' + \
            os.environ.get('GPTICEBOT_PORT')+'/regular_message'
        data = {
            "user_id": user_id,
            "message": message.text
        }
        request_str = json.dumps(data)
        content = requests.post(url, json=request_str)
        gpticebot.reply_to(message, content.text, parse_mode="MarkdownV2")
    except Exception as e:
        gpticebot.reply_to(message, e)


# receive audio from telegram
@gpticebot.message_handler(func=lambda message: True, content_types=['voice'])
def echo_voice(message):
    logger.info("gpticebot - voice message from user: " + str(message.from_user.id))
    file_info = gpticebot.get_file(message.voice.file_id)
    downloaded_file = gpticebot.download_file(file_info.file_path)
    url = 'http://localhost:'+os.environ.get('GPTICEBOT_PORT')+'/voice_message'
    # send user_id + voice as bytes, via post
    logger.info("gpticebot - calling url: " + url)
    r = requests.post(url, files={
        'user_id': message.from_user.id,
        'voice': downloaded_file
    })
    logger.info("gpticebot - response code: " + str(r.status_code))
    logger.info("gpticebot - response headers: " + str(r.headers))

    # There is two types of response:
    # 1. text: return web.Response(text=message, content_type="text/html")
    # 2. audio file: return web.Response(body=content, content_type="audio/wav")
    # Check type, if response is text
    if r.headers['content-type'] == 'text/html; charset=utf-8':
        gpticebot.reply_to(message, r.text, parse_mode="MarkdownV2")
        return
    else:
        # response returned as
        # web.FileResponse(filename+'.wav')
        # return as audio message
        gpticebot.send_voice(message.chat.id, r.content)


@gpticebot.inline_handler(func=lambda chosen_inline_result: True)
def query_text(inline_query):
    url = 'http://localhost:' + \
        os.environ.get('GPTICEBOT_PORT')+'/inline'
    data = {
        "user_id": inline_query.from_user.id,
        "query": inline_query.query
        }
    request_str = json.dumps(data)
    content = requests.post(url, json=request_str)
    
    # answer 0
    r0 = telebot.types.InlineQueryResultArticle(
        '0',
        content.json()['result'],
        telebot.types.InputTextMessageContent(content.json()['result']),
    )
    answer = [r0]

    gpticebot.answer_inline_query(
        inline_query.id,
        answer,
        cache_time=0,
        is_personal=True
    )
# === === === gpticebot --

def main():
    logger.info("main: Starting server")
    app = web.Application()
    app.router.add_post('/{token}/', handle)
    app.router.add_route('GET', '/test', call_test)
    # Build ssl context
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

    # Start aiohttp server
    web.run_app(
        app,
        host=WEBHOOK_LISTEN,
        port=os.environ.get('DOCKER_PORT', ''),
        ssl_context=context
    )


if __name__ == "__main__":
        main()
