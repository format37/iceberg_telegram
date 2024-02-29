from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import os
import logging
import telebot
import uuid
from iceberg import (
    get_keyboard,
    contact_reaction,
    get_bid_list,
    read_config,
    save_config,
    get_bid_keyboard
)

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


@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    logger.info('post: message')
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

    # Return if it is a group
    if message['chat']['type'] != 'private':
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."

    conf_path = './data/user_conf/'
    config = read_config(conf_path, message['from']['id'])
    data_path = './data/'

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
    
    elif 'photo' in message or 'document' in message:

        if 'photo' in message:
            logger.info("photo in message")
            photo = message['photo']
            if len(photo) > 0:
                # Photo is a photo
                file_id = photo[-1]['file_id']
                logger.info("mrmsupport_bot. file_id: "+str(file_id))

        elif 'document' in message:
            logger.info("document in message")
            document = message['document']
            if document['mime_type'].startswith('image/'):
                # Document is a photo
                file_id = document['file_id']
                logger.info("mrmsupport_bot. file_id: "+str(file_id))
                
        bot = telebot.TeleBot(token)
        # file_id = message['document']['file_id']
        logger.info("mrmsupport_bot_test. file_id: "+str(file_id))
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        # Replace file_id to uid
        file_id = str(uuid.uuid4())
        
        bid_id = config['last_cmd'].split(':')[1]
        # bid_folder = data_path+'photos/'+user_id+'/'+config['last_cmd'].split(':')[1]
        bid_folder = os.path.join(data_path, 'photos', str(message['from']['id']), bid_id)
        # Create a folder if not exists
        if not os.path.exists(bid_folder):
            os.makedirs(bid_folder)
            logger.info("bid_folder created: "+str(bid_folder))
        photo_loaded = False

        # Save the file, get the file extension
        file_path = os.path.join(bid_folder, file_id+'.'+file_info.file_path.split('.')[-1])
        # Create folder if not exists
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            photo_loaded = True
            logger.info("Download successfull. file_path: "+str(file_path))

        # Send a message to the user
        if photo_loaded:
            answer = 'Успешно загружено фото для заявки: '+config['last_cmd'].split(':')[1]
            return JSONResponse(content={
                "type": "text",
                "body": str(answer)
            })
        else:
            answer = 'Не удалось загрузить фото для заявки: '+config['last_cmd'].split(':')[1]
            return JSONResponse(content={
                "type": "text",
                "body": str(answer)
            })

    elif message['text'] == 'Заявки':
        answer = 'Функция получения заявок временно недоступна. Приносим извенение за доставленные неудобства.'
        # Return this when debugging
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })"""
        
        conf_path = './data/user_conf/'
        
        config = read_config(conf_path, message['from']['id'])
        
        # Load bid list
        bid_list = get_bid_list(message['from']['id'], clientPath)
        
        # Save bid list to config
        config['bid_list'] = bid_list

        if len(bid_list) == 0:
            answer = 'Список заявок пуст'
            return JSONResponse(content={
                "type": "text",
                "body": str(answer)
                })
        
        config['bid_list_page'] = 1
        keyboard_dict, current_page = get_bid_keyboard(config, '')

        config['last_cmd'] = 'bid_list'
        logger.info("mrmsupport_bot_test. b. last_cmd: "+str(config['last_cmd']))
        config['bid_list_page'] = current_page
        logger.info(f'Saving config from message: {message}')
        save_config(conf_path, config, message['from']['id'])
        
        logger.info("mrmsupport_bot. b. keyboard_dict: "+str(keyboard_dict))
        
        # Send the message with the keyboard
        return JSONResponse(content={
            "type": "keyboard",
            "keyboard_type": "inline",
            "body": keyboard_dict
            })
    
    elif message['text'] == 'Скачать приложение' and message['chat']['type'] == 'private':
        apk_link = 'http://service.icecorp.ru/mrm/apk/807.apk' # Default link
        try:
            apt_list_path = '/mnt/soft/apk'
            # Find the name of the latest apk, using sorting by name descending
            for file in sorted(os.listdir(apt_list_path), reverse=True):
                if file.endswith(".apk"):
                    logger.info("mrmsupport_bot_test. latest apk: "+str(file))
                    apk_link = 'https://soft.iceberg.ru/apk/'+file
                    break
        except Exception as e:
            logger.error("mrmsupport_bot_test. apk_link: "+str(e))
        answer = 'Скачать приложение можно по ссылке:\n'+apk_link
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })
    elif message['text'] == 'Скачать Updater' and message['chat']['type'] == 'private':
        apk_link = 'http://mpk.iceberg.ru:45080/updater.apk' # Static link
        answer = 'Скачать Updater можно по ссылке:\n'+apk_link
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })
    else:
        # elif message['text'] == '/start':
        keyboard_dict = get_keyboard(message['text'])

        return JSONResponse(content={
            "type": "keyboard",
            "body": keyboard_dict
            })



@app.post("/callback")
async def call_callback(request: Request, authorization: str = Header(None)):
    logger.info('post: callback')
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
    call = await request.json()
    logger.info(f'call: {call}')

    # Return if it is a group
    if call['message']['chat']['type'] != 'private':
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    conf_path = './data/user_conf/'
    config = read_config(conf_path, call['message']['chat']['id'])

    if call['data'] in ['btn:<','btn:>']:
        keyboard_dict, current_page = get_bid_keyboard(config, call['data'])
        config['bid_list_page'] = current_page
        save_config(conf_path, config, call['message']['chat']['id'])

        # Send the message with the keyboard
        return JSONResponse(content={
            "type": "keyboard",
            "keyboard_type": "inline",
            "body": keyboard_dict
            })
    
    elif call['data'].startswith('bid:'):
        option = call['data'].split(':')[1]
        config['last_cmd'] = 'bid:'+option
        save_config(conf_path, config, call['message']['chat']['id'])
        buttons = []
        bid_buttons = []
        button = {
            "text": 'Загрузить фото',
            "callback_data": f'upload_photo:{option}'
        }
        bid_buttons.append(button)
        buttons.append(bid_buttons)
        keyboard_message = 'Заявка: '+option
        keyboard_dict = {
            "message": keyboard_message,
            "row_width": 1,
            "resize_keyboard": True,
            "buttons": buttons
        }
        # Send the message with the keyboard
        return JSONResponse(content={
            "type": "keyboard",
            "keyboard_type": "inline",
            "body": keyboard_dict
            })

    elif call['data'].startswith('upload_photo:'):
        config['last_cmd'] = call['data']
        save_config(conf_path, config, call['message']['chat']['id'])
        logger.info("mrmsupport_bot_test. u. last_cmd: "+str(config['last_cmd']))
        answer = 'Пожалуйста, загрузите фото без сжатия'
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })
