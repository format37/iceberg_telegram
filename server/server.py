from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import telebot
import os
import logging
import ssl


# mrm_support_redirect,
# escape_characters
from iceberg import (    
    bot_start,
    contact,
    mrm_support_receive_photo,
    mrm_support_text,
    mrm_support_bot_button_handler,
    mrm_support_redirect
)
# import math

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



# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables 
WEBHOOK_HOST = os.environ.get('WEBHOOK_HOST', '')  
WEBHOOK_PORT = os.environ.get('WEBHOOK_PORT', '')
WEBHOOK_SSL_CERT = 'webhook_cert.pem'
WEBHOOK_SSL_PRIV = 'webhook_pkey.pem'

# Initialize bots
bots = []

def init_bot(token):
    bot = telebot.TeleBot(token)
    
    url = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/{token}/"
    bot.remove_webhook()
    bot.set_webhook(url=url, certificate=open(WEBHOOK_SSL_CERT, 'r'))
    
    bots.append(bot)
    return bot

@app.post("/{token}/")
async def handle(request: Request, token: str):
    update = telebot.types.Update.de_json(await request.json())
    for bot in bots:
        if bot.token == token:
            bot.process_new_updates([update])
            return JSONResponse({"ok": True})
    raise HTTPException(status_code=403, detail="Invalid token")
            
@app.on_event("startup")
async def startup():
    # Create bots
    init_bot(os.environ['BOT1_TOKEN']) 
    init_bot(os.environ['BOT2_TOKEN'])
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2) 
    context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)
    app.state.ssl_context = context


# === === === partners_iceberg_bot ++
partners_iceberg_bot = init_bot(os.environ['PARTNERS_ICEBERG_BOT_TOKEN'])

@app.post("/partners_iceberg_bot/start")
async def partners_iceberg_bot_start(update: telebot.types.Update):
    # Call bot_start function
    return JSONResponse({"ok": True})

@app.post("/partners_iceberg_bot/contact")  
async def partners_iceberg_bot_contact(update: telebot.types.Update):
    # Call contact function
    return JSONResponse({"ok": True}) 

@app.post("/partners_iceberg_bot/{message_type}")
async def partners_iceberg_bot_message(message_type: str, update: telebot.types.Update):
    # Call appropriate message handler based on type
    if message_type == "text":
        handle_text_message(update)
    elif message_type == "photo":
        handle_photo_message(update)
        
    return JSONResponse({"ok": True})
# === === === partners_iceberg_bot --


# === === === mrminfobot ++
# Initialize bot
mrminfobot = init_bot(os.environ['MRMINFOBOT_TOKEN'])

@app.post("/mrminfobot/{message_type}")  
async def mrminfobot_message(message_type: str, update: telebot.types.Update):
    
    if message_type in ["text", "photo", "video", "document", "audio", "voice", "location", "contact", "sticker"]:
        # Call mrm_support_redirect 
        return JSONResponse({"ok": True})

    else:
        return HTTPException(status_code=400, detail="Invalid message type")
        
# Handle callbacks        
@app.post("/mrminfobot/callback")
async def mrminfobot_callback(update: telebot.types.Update):
    message = update.callback_query
    mrm_support_redirect(message, mrminfobot, logger, clientPath_prod)
    return JSONResponse({"ok": True})
# === === === mrminfobot --


# === === === mrmsupport_bot ++
# Initialize bot
mrmsupport_bot = init_bot(os.environ['MRMSUPPORTBOT_TOKEN'])

# Handle start command
@app.post("/mrmsupport_bot/start")  
async def mrmsupport_bot_start(update: telebot.types.Update):
    # bot_start(update)  
    message = update.message
    bot_start(message, mrmsupport_bot, logger)
    return JSONResponse({"ok": True})

# Handle contact
@app.post("/mrmsupport_bot/contact")
async def mrmsupport_bot_contact(update: telebot.types.Update):
    # contact(update)
    message = update.message
    contact(message, mrmsupport_bot, logger, clientPath_test, 'mrmsupport_bot')
    return JSONResponse({"ok": True})

# Handle messages
@app.post("/mrmsupport_bot/{message_type}") 
async def mrmsupport_bot_message(message_type: str, update: telebot.types.Update):
    if message_type == "text":
        # mrm_support_text(update)
        message = update.message
        mrm_support_text(
            message = message,
            bot = mrmsupport_bot,
            logger = logger,
            data_path = DATA_PATH_PROD,
            clientPath = clientPath_prod,
            row_width = 3,
            max_buttons_per_page = 14
        )
    elif message_type in ["photo", "document"]:
        # mrm_support_receive_photo(update)
        message = update.message
        mrm_support_receive_photo(message, mrmsupport_bot, logger, DATA_PATH_PROD)
    else:
        raise HTTPException(status_code=400, detail="Invalid message type")
        
    return JSONResponse({"ok": True})
    
# Handle callbacks
@app.post("/mrmsupport_bot/callback")
async def mrmsupport_bot_callback(update: telebot.types.Update):
   # mrm_support_bot_button_handler(update)
   call = update.callback_query
   mrm_support_bot_button_handler(
        call = call,
        bot = mrmsupport_bot,
        logger = logger,
        data_path = DATA_PATH_PROD,
        row_width = 3,
        max_buttons_per_page = 14
        )
   return JSONResponse({"ok": True})
# === === === mrmsupport_bot --

    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=WEBHOOK_HOST, port=WEBHOOK_PORT, ssl_keyfile=WEBHOOK_SSL_PRIV, ssl_certfile=WEBHOOK_SSL_CERT)