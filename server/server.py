#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ssl
import os
from aiohttp import web
import telebot
from telebot import types
from telebot import apihelper


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


async def call_test(request):
        content = "get ok"
        return web.Response(text=content, content_type="text/html")


def get_token(bot_token_env):
    return os.environ.get(bot_token_env, '')


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


# === === === mrmsupport_bot ++
# mrmsupport_bot_SCRIPT_PATH = '/home/dvasilev/projects/telegram_bots/mrmsupport_bot/'
# mrmsupport_bot = default_bot_init(WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_SSL_CERT, mrmsupport_bot_SCRIPT_PATH)
mrmsupport_bot = default_bot_init('MRMSUPPORTBOT_TOKEN')
bots.append(mrmsupport_bot)
# sys.path.append(mrmsupport_bot_SCRIPT_PATH)
from Telegram_phoneConfirmation import mrmsupport_bot_confirmphone
from Telegram_phoneConfirmation import mrmsupport_bot_writelink

@mrmsupport_bot.message_handler(commands=['user'])
def idbot_user(message):
	mrmsupport_bot.reply_to(message, str(message.from_user.id))

@mrmsupport_bot.message_handler(commands=['start'])
def idbot_user(message):
	keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)  # Подключаем клавиатуру
	button_phone = types.KeyboardButton(text="☎ Нажмите чтобы отправить Ваш контакт",request_contact=True)  # Указываем название кнопки, которая появится у пользователя
	keyboard.add(button_phone)  # Добавляем эту кнопку
	mrmsupport_bot.send_message(message.chat.id, 'Нажмите на кнопку ниже',reply_markup=keyboard)  # Дублируем сообщением о том, что пользователь сейчас отправит боту свой номер телефона (на всякий случай, но это не обязательно)

@mrmsupport_bot.message_handler(content_types=['contact']) #Объявили ветку, в которой прописываем логику на тот случай, если пользователь решит прислать номер телефона :)
def idbot_user(message):
	if message.contact is not None: #Если присланный объект <strong>contact</strong> не равен нулю
		# print(message.contact) #Выводим у себя в панели контактные данные. А вообщем можно их, например, сохранить или сделать что-то еще.
		idfrom=message.from_user.id
		idcontact = message.contact.user_id

		if not idcontact==idfrom:
			mrmsupport_bot.reply_to(message, 'Подтвердить можно только свой номер телефона!')
		else:
			try:
				res=mrmsupport_bot_confirmphone(message.contact.phone_number, message.chat.id)

				if res:
					if res['result']:
						if res['link'] and not res['link']=='':
							mrmsupport_bot.reply_to(message,
													'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' +
													res['link'])
						else:
							method_url = 'createChatInviteLink'
							payload = {'chat_id': res['chat_id'],'member_limit':1}
							link= apihelper._make_request(get_token('MRMSUPPORTBOT_TOKEN'), method_url, params=payload, method='post')
							mrmsupport_bot_writelink(message.contact.phone_number,link['invite_link'])
							mrmsupport_bot.reply_to(message,'Вы успешно прошли авторизацию, вот ссылка для вступления в группу '+link['invite_link'])

					else:
						mrmsupport_bot.reply_to(message, 'Ваш контакт не найден, обратитесь к администратору')
				else:
					mrmsupport_bot.reply_to(message, 'Ваш контакт не найден, обратитесь к администратору')
			except Exception as e:
				mrmsupport_bot.reply_to(message, str(e))


@mrmsupport_bot.message_handler(commands=['group'])
def idbot_group(message):
	mrmsupport_bot.reply_to(message, str(message.chat.id))
# === === === mrmsupport_bot --


def main():

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
        ssl_context=context,
    )


if __name__ == "__main__":
        main()
