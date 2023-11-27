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
from math import ceil

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
    
def mrmsupport_bot_confirmphone(phoneNumber,chatId, clientPath,username):
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)
    
    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        res = client.service.phoneConfirmation(phoneNumber, chatId,username)
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

def contact_reaction(message, clientPath, token):
    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."
    idfrom = message['from']['id']
    idcontact = message['contact']['user_id']
    username= message['contact']['username']

    if not idcontact==idfrom:
        answer = 'Подтвердить можно только свой номер телефона.'
    else:
        logger.info('contact_reaction. message: '+str(message))

        try:
            results = mrmsupport_bot_confirmphone(message['contact']['phone_number'], message['chat']['id'], clientPath ,username) 
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

    return answer

def get_bid_list(user_id, clientPath):
    user        = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN')
    password    = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD')

    session = Session()
    session.auth = HTTPBasicAuth(user, password)

    client_list = []
    for client in clientPath:
        client_list.append(Client(client, transport=Transport(session=session)))

    bid_list = []
    for client in client_list:
        try:
            resultCreateRequestLK = client.service.TelegramBidList(user_id)
            logger.info(f'get_bid_list {user_id} resultCreateRequestLK bids count: {len(resultCreateRequestLK["Bids"])}')
            for bid in resultCreateRequestLK['Bids']:
                if bid['status'] == 'Закрыта' or bid['status'] == 'Готова':
                    continue
                bid_structure = {
                    'id': bid['id'],
                    'status': bid['status'],
                    'address': {
                        'city': str(bid['address']['city'])
                    }
                }
                # logger.info('bid structure: '+str(bid_structure))
                # logger.info('city: '+str(bid['address']['city']))
                bid_list.append(bid_structure)
                # bid_list.append(bid['id'])
                # bid['address']['city']
        except Exception as e:
            logger.error('err: '+str(e))
    
    logger.info(f'get_bid_list {user_id} bid_list count: {len(bid_list)}')
    return bid_list

def load_default_config():
    with open('data/user_conf/config.json', 'r') as f:
        config = json.load(f)
    return config

def reinit_config(default_config, user_config):
    # reinit user config
    for key in default_config.keys():
        if key not in user_config.keys():
            user_config[key] = default_config[key]
    return user_config

def read_config(conf_path, user_id):
    # if user.json conf not in user_conf folder, create it
    """if not os.path.exists(conf_path):
        logger.info(f'read_config: Creating folder {conf_path}')
        os.makedirs(conf_path)"""
    # default config file: config.json
    if not os.path.exists(conf_path+str(user_id)+'.json'):
        config = load_default_config()
    else:
        with open(conf_path+str(user_id)+'.json', 'r') as f:
            config = json.load(f)
            config = reinit_config(load_default_config(), config)
    return config

def save_config(conf_path, config, user_id):
    logger.info(f'save_config: {conf_path+str(user_id)+".json"}')
    with open(conf_path+str(user_id)+'.json', 'w') as f:
        json.dump(config, f)

@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    logger.info('call_message')
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    if token:
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

    # Return if it is a group
    if message['chat']['type'] != 'private':
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."

    clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
    ]
    
    if 'contact' in message:
        answer = contact_reaction(message, clientPath, token)
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })
    
    # data_path = "./data/" + str(message['chat']['id'])
    # data_path = "./data"
    # Create folder if not exists
    """if not os.path.exists(data_path):
        os.makedirs(data_path)"""

    if message['text'] == '/start':
        keyboard_dict = get_keyboard(message['text'])

        return JSONResponse(content={
            "type": "keyboard",
            "body": keyboard_dict
            })

    if message['text'] == 'Заявки':
        answer = 'Функция получения заявок временно недоступна. Приносим извенение за доставленные неудобства.'
        # Return answer
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })"""
        conf_path = './data/user_conf/'
        
        # Create folder if not exists
        """if not os.path.exists(conf_path):
            os.makedirs(conf_path)"""
        
        config = read_config(conf_path, message['from']['id'])
        
        # Load bid list
        options = get_bid_list(message['from']['id'], clientPath)
        # TODO: rename options to bid_list
        
        # Save bid list to config
        config['bid_list'] = options

        if len(options) == 0:
            answer = 'Список заявок пуст'
            return JSONResponse(content={
                "type": "text",
                "body": str(answer)
                })
        
        current_page = 1
        logger.info("mrmsupport_bot_test. bidlist. current_page: "+str(current_page))
        max_buttons_per_page = 14
        # Calculate the total number of pages
        total_pages = ceil(len(options) / max_buttons_per_page)
        # Calculate the start and end index of the current page
        start_index = (current_page - 1) * max_buttons_per_page
        end_index = min(start_index + max_buttons_per_page, len(options))
        
        """
        {
            "Default": {
                "message": "Выберите команду",
                "row_width": 2,
                "resize_keyboard": true,
                "buttons": [
                        {
                            "text": "☎ Нажмите чтобы отправить Ваш контакт",
                            "request_contact": true
                        },
                        {
                            "text": "Скачать приложение",
                            "request_contact": false
                        },
                        {
                            "text": "Заявки",
                            "request_contact": false
                        }
                    ]
            }
        }
        """

        # Create the list of buttons for the current page
        buttons = []
        for i in range(start_index, end_index):
            # button = types.InlineKeyboardButton(options[i]['id'], callback_data='bid:'+options[i]['id'])
            button = {
                "text": options[i]['id'],
                "request_contact": False
            }
            buttons.append(button)

        # Create the list of navigation buttons
        navigation_buttons = []
        if current_page > 1:
            # navigation_buttons.append(types.InlineKeyboardButton('<', callback_data='btn:<'))
            navigation_buttons.append({
                "text": "<",
                "request_contact": False
            })
        if current_page < total_pages:
            # navigation_buttons.append(types.InlineKeyboardButton('>', callback_data='btn:>'))
            navigation_buttons.append({
                "text": ">",
                "request_contact": False
            })
        # Combine the buttons into a keyboard markup
        """keyboard = types.InlineKeyboardMarkup(row_width=row_width)
        keyboard.add(*buttons)
        keyboard.add(*navigation_buttons)"""
        keyboard_dict = {
            "message": "Выберите заявку",
            "row_width": 2,
            "resize_keyboard": True,
            "buttons": buttons
        }
        keyboard_dict['buttons'].append(navigation_buttons)

        config['last_cmd'] = 'bid_list'
        logger.info("mrmsupport_bot_test. b. last_cmd: "+str(config['last_cmd']))
        config['bid_list_page'] = current_page
        save_config(conf_path, config, message['from']['id'])

        # Send the message with the keyboard
        return JSONResponse(content={
            "type": "keyboard",
            "body": keyboard_dict
            })
        
        # TODO: implement exception handling

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
