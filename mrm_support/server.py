from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import os
import logging
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
import json
from telebot import apihelper

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})

def get_keyboard(current_screen):

    with open('data/menu.json') as f:
        menu = json.load(f)

    if current_screen in menu:
        message = menu[current_screen]['message']
        # keyboard_modificator(current_screen, user_session, menu, message)        
        return menu[current_screen]

    else:
        # Default to start screen
        return menu['Default']
    
def mrmsupport_bot_confirmphone(phoneNumber,chatId, clientPath):
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    
    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        res = client.service.phoneConfirmation(phoneNumber, chatId)
        if res and res['result']:
            logger.info('mrmsupport_bot_confirmphone. res: '+str(res))
            return [res]
    return  [res]

def mrmsupport_bot_writelink(phoneNumber,link, clientPath):
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        res = client.service.writeLink(phoneNumber, link)
        if res :
            return res
    return  res

"""@app.post("/message")
async def call_message(request: Request):
    logger.info('call_message')
    message = await request.json()
    """
@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    logger.info('call_message')
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    # Log the token or perform further actions
    if token:
        # logger.info(f'Token: {token}')
        pass
    else:
        answer = 'Не удалось определить токен бота. Пожалуйста обратитесь к администратору.'
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })

    message = await request.json()
    logger.info(f'message: {message}')
    """
    {
    "message_id":1069480,
    "from":{
        "id":1114994337,
        "is_bot":false,
        "first_name":"Ivan",
        "last_name":"Tit",
        "username":"ibrogim66",
        "language_code":"ru"
    },
    "chat":{
        "id":1114994337,
        "first_name":"Ivan",
        "last_name":"Tit",
        "username":"ibrogim66",
        "type":"private"
    },
    "date":1700736663,
    "contact":{
        "phone_number":"89124515182",
        "first_name":"Виктор",
        "last_name":"Бывальцев",
        "vcard":"BEGIN:VCARD\nVERSION:3.0\nN:Бывальцев;Виктор;;;\nFN:Виктор Бывальцев\nTEL;TYPE=CELL:891-245-15182\nEND:VCARD",
        "user_id":95221607
        }
    }
    """

    # if contact in message
    if 'contact' in message:
        idfrom = message['from']['id']
        idcontact = message['contact']['user_id']

        clientPath = [
            'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
            'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
            'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
        ]

        if not idcontact==idfrom:
            # bot.reply_to(message, 'Подтвердить можно только свой номер телефона!')
            answer = 'Подтвердить можно только свой номер телефона.'
            return JSONResponse(content={
                "type": "text",
                "body": str(answer)
            })
        else:
            # bot.reply_to(message, 'Спасибо, Ваш номер телефона подтвержден!')
            answer = 'Ошибка. Пожалуйста обратитесь к администратору.'

            try:
                results = mrmsupport_bot_confirmphone(message['contact']['phone_number'], message['chat']['id'], clientPath)

                # Check if any result is true
                # has_true_result = any(res.get('result') for res in results if res)
                has_true_result = any(res.get('result') if isinstance(res, dict) else False for res in results)

                if has_true_result:
                    # Process each result
                    for res in results:
                        if res and res['result']:
                            has_true_result = True
                            # Keyboard initialization
                            # Send message with keyboard
                            if res['link'] and not res['link']=='':
                                answer = 'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' + res['link']                                
                            else:
                                method_url = 'createChatInviteLink'
                                payload = {'chat_id': res['chat_id'],'member_limit':1}
                                link= apihelper._make_request(token, method_url, params=payload, method='post')
                                mrmsupport_bot_writelink(message.contact.phone_number,link['invite_link'], clientPath)
                                answer = 'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' + link['invite_link']
                else:
                    answer = 'Ваш контакт не найден. Пожалуйста, обратитесь к администратору.'
            except Exception as e:
                logger.error("Error in contact handling: {}".format(str(e)))
                answer = f'Ошибка: {e}\nПожалуйста обратитесь к администратору.'


            return JSONResponse(content={
                "type": "text",
                "body": str(answer)
            })

    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."

    """if str(message['chat']['id']) in granted_chats:
        logger.info(str(message['chat']['id'])+' in granted_chats')
        # if message.forward_from is not None:
        if 'forward_from' in message:
            # logger.info('Received redirect from user id: '+str(message.forward_from.id))
            logger.info('Received redirect from user id: '+str(message['forward_from']['id']))
            reply = '[\n'
            # results = mrmsupport_bot_user_info(message.forward_from.id, clientPath)
            results = mrmsupport_bot_user_info(message['forward_from']['id'], clientPath)
            
            if len(results) == 0:
                answer = 'User not found'
                logger.info(answer)
            else:
                reply += ',\n'.join(results)
                answer = reply + '\n]'
                # logger.info('Replying in '+str(message.chat.id))
                logger.info('Replying in '+str(message['chat']['id']))
        else:
            answer = 'Unable to retrieve master information: forward_from is not defined.'
            logger.info(answer)

    return JSONResponse(content={
        "type": "text",
        "body": str(answer)
        })"""
    
    # Return if it is a group
    if message['chat']['type'] != 'private':
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    data_path = "./data/" + str(message['chat']['id'])
    # Create folder if not exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    if message['text'] == '/start':
        answer = 'Добро пожаловать!\n Я нахожусь на обслуживании.'

        """# Keyboard initialization
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        # Keyboard button initialization
        button_phone = types.KeyboardButton(text="☎ Нажмите чтобы отправить Ваш контакт",request_contact=True)
        keyboard.add(button_phone)
        button_app = types.KeyboardButton(text="Скачать приложение")
        keyboard.add(button_app)
        button_bid = types.KeyboardButton(text="Заявки")"""

        keyboard_dict = get_keyboard(message['text'])

        return JSONResponse(content={
            "type": "keyboard",
            "body": keyboard_dict
            })
        
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })"""
    # if message['text'] == 'Скачать приложение' and message.chat.type != 'group' and message.chat.type != 'supergroup':
    if message['text'] == 'Скачать приложение' and message['chat']['type'] == 'private':
        apk_link = 'http://service.icecorp.ru/mrm/apk/702.apk'
        try:
            apt_list_path = '/mnt/soft/apk'
            # Find the name of the latest apk, using sorting by name descending
            for file in sorted(os.listdir(apt_list_path), reverse=True):
                if file.endswith(".apk"):
                    apk_link = 'https://soft.iceberg.ru/apk/'+file
                    break
        except Exception as e:
            logger.error("mrmsupport_bot_test. apk_link: "+str(e))
        # bot.reply_to(message, 'Скачать приложение можно по ссылке:\n'+apk_link)
        answer = 'Скачать приложение можно по ссылке:\n'+apk_link
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })
    else:
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
