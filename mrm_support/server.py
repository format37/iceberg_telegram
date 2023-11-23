from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import logging
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport

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
async def call_message(request: Request):
    logger.info('call_message')
    message = await request.json()
    logger.info(message)
    """
    {
        'message_id': 89, 
        'from': {
            'id': 106129214, 
            'is_bot': False, 
            'first_name': 'Alex', 
            'username': 'format37', 
            'language_code': 'en', 
            'is_premium': True
        }, 
        'chat': {
            'id': -1001533625926, 
            'title': 'Bot factory 2', 
            'type': 'supergroup'
        }, 
        'date': 1699863766, 
        'forward_from': {
            'id': 106129214, 
            'is_bot': False, 
            'first_name': 'Alex', 
            'username': 'format37', 
            'language_code': 'en', 
            'is_premium': True
        }, 
        'forward_date': 1678700186, 
        'text': 'hello'
    }
    """

    clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
    ]

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
        """ keyboard_dict = get_keyboard(user_session, message['text'])

        return JSONResponse(content={
            "type": "keyboard",
            "body": keyboard_dict
            })"""
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
            })
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
