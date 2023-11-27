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
            logger.info('mrmsupport_bot_confirmphone A. res: '+str(res))
            return [res]
    logger.info('mrmsupport_bot_confirmphone B. res: '+str(res))
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

def contact_reaction(message):
    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."
    idfrom = message['from']['id']
    idcontact = message['contact']['user_id']

    clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
    ]

    if not idcontact==idfrom:
        answer = 'Подтвердить можно только свой номер телефона.'
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })"""
    else:
        # answer = 'Ошибка. Пожалуйста обратитесь к администратору.'
        logger.info('contact_reaction. message: '+str(message))

        try:
            results = mrmsupport_bot_confirmphone(message['contact']['phone_number'], message['chat']['id'], clientPath)
            has_true_result = False
            for res in results:
                if res:
                    if res['result']:
                        has_true_result = True

            if has_true_result:
                # Process each result
                for res in results:
                    if res and res['result']:
                        has_true_result = True
                        if res['link'] and not res['link']=='':
                            answer = 'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' + res['link']                                
                        else:
                            method_url = 'createChatInviteLink'
                            payload = {'chat_id': res['chat_id'],'member_limit':1}
                            link= apihelper._make_request(token, method_url, params=payload, method='post')
                            mrmsupport_bot_writelink(message['contact']['phone_number'],link['invite_link'], clientPath)
                            answer = 'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' + link['invite_link']
            else:
                answer = 'Ваш контакт не найден. Пожалуйста, обратитесь к администратору.'
        except Exception as e:
            logger.error("Error in contact handling: {}".format(str(e)))
            answer = f'Ошибка: {e}\nПожалуйста обратитесь к администратору.'


        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })"""
    return answer

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
    
    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."

    # Return if it is a group
    if message['chat']['type'] != 'private':
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    if 'contact' in message:
        answer = contact_reaction(message)
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })
    
    data_path = "./data/" + str(message['chat']['id'])
    # Create folder if not exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    if message['text'] == '/start':
        keyboard_dict = get_keyboard(message['text'])

        return JSONResponse(content={
            "type": "keyboard",
            "body": keyboard_dict
            })

    if message['text'] == 'Заявки':
        answer = 'Функция получения заявок временно недоступна. Приносим извенение за доставленные неудобства.'
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })
    
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
