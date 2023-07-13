import json
import os
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
from telebot import types
from telebot import apihelper
from math import ceil
import uuid
import logging


def escape_characters(text):
    """ https://core.telegram.org/bots/api#formatting-options
    Please note:

    Any character with code between 1 and 126 inclusively can be escaped anywhere with a preceding '\' character, in which case it is treated as an ordinary character and not a part of the markup. This implies that '\' character usually must be escaped with a preceding '\' character.
    Inside pre and code entities, all '`' and '\' characters must be escaped with a preceding '\' character.
    Inside (...) part of inline link definition, all ')' and '\' must be escaped with a preceding '\' character.
    In all other places characters '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!' must be escaped with the preceding character '\'.
    In case of ambiguity between italic and underline entities __ is always greadily treated from left to right as beginning or end of underline entity, so instead of ___italic underline___ use ___italic underline_\r__, where \r is a character with code 13, which will be ignored.
    """
    # characters = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    characters = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for character in characters:
        text = text.replace(character, '\\'+character)
    return text


def get_token(bot_token_env):
    return os.environ.get(bot_token_env, '')


def partners_bot_confirmphone(phoneNumber, chatId, clientPath):

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    """clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
        ]"""
    # clientPath = ['http://10.2.4.141/Test_Piter_MRM/ws/Telegram.1cws?wsdl']
    results = []
    try:
        # Get only the right 10 symbols of the phone number
        phoneNumber = phoneNumber.replace('+','')[-10:]
        logger.info('phoneNumber: ' + phoneNumber)
        logger.info('type: ' + str(type(phoneNumber)))
        for w in clientPath:
            client = Client(w, transport=Transport(session=session))
            res = client.service.partnersPhoneConfirmation(phoneNumber, chatId)
            results.append(res)
    except Exception as e:
        logger.error(e)
    return results


def mrmsupport_bot_confirmphone(phoneNumber,chatId, clientPath):
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    
    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        res = client.service.phoneConfirmation(phoneNumber, chatId)
        if res and res['result']:
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


def mrmsupport_bot_user_info(user_id, clientPath, logger):
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    results = []
    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        logger.info('Calling user_info from: ' + str(w))
        try:
            res = client.service.user_info(user_id, '')
            logger.info('user_info result: ' + str(res))
            # code		= res.result.code
            # message		= res.result.message
            if res and res['result']:
                results.append(str(res))
        except Exception as e:
            logger.error(str(w) + ' user_info error: ' + str(e))
    logger.info('user_info results count: ' + str(len(results)))
    return results


def load_default_config(conf_path):
# conf_path = 'data/user_conf/'
    with open(conf_path+'config.json', 'r') as f:
        config = json.load(f)
    return config

def reinit_config(default_config, user_config):
    # reinit user config
    for key in default_config.keys():
        if key not in user_config.keys():
            user_config[key] = default_config[key]
    return user_config


def read_config(conf_path, user_id):
    # conf_path = 'data/user_conf/'
    # if user.json conf not in user_conf folder, create it
    # default config file: config.json
    if not os.path.exists(conf_path+str(user_id)+'.json'):
        config = load_default_config(conf_path)
    else:
        with open(conf_path+str(user_id)+'.json', 'r') as f:
            config = json.load(f)
            config = reinit_config(load_default_config(conf_path), config)
    return config


def save_config(conf_path, config, user_id):
    with open(conf_path+str(user_id)+'.json', 'w') as f:
        json.dump(config, f)

def bid_list(user_id, clientPath, logger):
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
    
    return bid_list

def bot_start(message, mrmsupport_bot_test, logger):
    # Return if it is a group
    if message.chat.type != 'private':
        return
    logger.info("mrmsupport_bot_test. Start: "+str(message.from_user.id)+' '+message.text)
    # Keyboard initialization
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    # Keyboard button initialization
    button_phone = types.KeyboardButton(text="☎ Нажмите чтобы отправить Ваш контакт",request_contact=True)
    keyboard.add(button_phone)
    button_app = types.KeyboardButton(text="Скачать приложение")
    keyboard.add(button_app)
    button_bid = types.KeyboardButton(text="Заявки")
    keyboard.add(button_bid)
    # Send message with keyboard
    mrmsupport_bot_test.send_message(message.chat.id, 'Пожалуйста, отправьте ваш контакт для регистрации', reply_markup=keyboard)


def contact(message, bot, logger, clientPath, bot_name):
    # Return if it is a group
    if message.chat.type != 'private':
        return
    logger.info("contact: "+str(message.from_user.id))
    logger.info(str(message.contact))
    if message.contact is not None:
        idfrom=message.from_user.id
        idcontact = message.contact.user_id

        if not idcontact==idfrom:
            bot.reply_to(message, 'Подтвердить можно только свой номер телефона!')
        else:
            try:
                if bot_name == 'mrmsupport_bot':
                    results = mrmsupport_bot_confirmphone(message.contact.phone_number, message.chat.id, clientPath)
                else:
                    results = partners_bot_confirmphone(message.contact.phone_number, message.chat.id, clientPath)

                # for res in results:
                # Initialize a variable to keep track of whether at least one result is True
                has_true_result = False

                for res in results:
                    if res:
                        if res['result']:
                            has_true_result = True

                if has_true_result:

                    for res in results:
                        # Initialize a variable to keep track of whether at least one result is True
                        # has_true_result = False

                        for res in results:
                            if res:
                                if res['result']:
                                    has_true_result = True
                                    # Keyboard initialization
                                    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                                    button_phone = types.KeyboardButton(text="☎ Нажмите чтобы отправить Ваш контакт",request_contact=True)
                                    keyboard.add(button_phone)
                                    button_app = types.KeyboardButton(text="Скачать приложение")
                                    keyboard.add(button_app)
                                    button_bid = types.KeyboardButton(text="Заявки")
                                    keyboard.add(button_bid)
                                    # Send message with keyboard
                                    if res['link'] and not res['link']=='':
                                        if bot_name == 'mrmsupport_bot':
                                            message_text = 'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' + res['link']
                                        else:
                                            message_text = 'Вы успешно прошли авторизацию'                                
                                        bot.reply_to(
                                            message,
                                            message_text,
                                            reply_markup=keyboard
                                        )
                                    else:
                                        method_url = 'createChatInviteLink'
                                        payload = {'chat_id': res['chat_id'],'member_limit':1}
                                        link= apihelper._make_request(get_token('MRMSUPPORTBOT_TOKEN'), method_url, params=payload, method='post')
                                        mrmsupport_bot_writelink(message.contact.phone_number,link['invite_link'], clientPath)
                                        if bot_name == 'mrmsupport_bot':
                                            message_text = 'Вы успешно прошли авторизацию, вот ссылка для вступления в группу ' + link['invite_link']
                                        else:
                                            message_text = 'Вы успешно прошли авторизацию'
                                        bot.reply_to(
                                            message,
                                            message_text,
                                            reply_markup=keyboard
                                        )

                else:
                    bot.reply_to(message, 'Ваш контакт не найден. Пожалуйста, обратитесь к администратору')
            except Exception as e:
                bot.reply_to(message, str(e))


def mrm_support_receive_photo(message, bot, logger, data_path):
    try:
        # Return if it is a group
        if message.chat.type != 'private':
            return
        # Create folder if not exists
        if not os.path.exists(data_path):
            os.makedirs(data_path)
        # logger.info("mrmsupport_bot_test => Photo: "+str(message.from_user.id))
        conf_path = data_path+'user_conf/'
        # Create folder if not exists
        if not os.path.exists(conf_path):
            os.makedirs(conf_path)
        config = read_config(conf_path, message.from_user.id)
        logger.info("mrm_support_receive_photo from "+str(message.from_user.id)+": "+str(config['last_cmd']))
        if config['last_cmd'].startswith('upload_photo:') or config['last_cmd'].startswith('bid:'):
            
            # logger.info("mrmsupport_bot_test. photo. last_cmd: "+str(config['last_cmd']))
            # Create a folder if not exists
            if not os.path.exists(data_path+'photos'):
                os.makedirs(data_path+'photos')
            user_id = str(message.from_user.id)
            # create user id folder if not exists
            if not os.path.exists(data_path+'photos/'+user_id):
                os.makedirs(data_path+'photos/'+user_id)
            # Define the bid folder
            bid_folder = data_path+'photos/'+user_id+'/'+config['last_cmd'].split(':')[1]
            # Create the bid folder if not exists
            if not os.path.exists(bid_folder):
                os.makedirs(bid_folder)
            photo_loaded = False
            if message.photo is not None:
                # Get the file_id of the photo
                file_id = message.photo[-1].file_id
                # Get the file info
                file_info = bot.get_file(file_id)
                # Download the file
                downloaded_file = bot.download_file(file_info.file_path)
                # logger.info("mrmsupport_bot_test. photo: "+str(message.from_user.id)+" "+str(file_id)+" "+file_info.file_path)
                # Save the file
                # with open(bid_folder+'/'+file_id+'.jpg', 'wb') as new_file:
                
                # Replace file_id to uid
                file_id = str(uuid.uuid4())
                # Save the file, get the file extension
                file_path = bid_folder+'/'+file_id+'.'+file_info.file_path.split('.')[-1]
                with open(file_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                    photo_loaded = True

            elif message.document is not None:
                # Get the file_id of the photo
                file_id = message.document.file_id
                # Get the file info
                file_info = bot.get_file(file_id)
                # Download the file
                downloaded_file = bot.download_file(file_info.file_path)
                # logger.info("mrmsupport_bot_test. document: "+str(message.from_user.id)+" "+str(file_id)+" "+file_info.file_path)
                
                # Replace file_id to uid
                file_id = str(uuid.uuid4())
                # Save the file
                file_path = bid_folder+'/'+file_id+'.'+message.document.file_name.split('.')[-1]
                with open(file_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                    photo_loaded = True

            # Send a message to the user
            if photo_loaded:
                bot.reply_to(message, 'Успешно загружено фото для заявки: '+config['last_cmd'].split(':')[1])
            else:
                bot.reply_to(message, 'Не удалось загрузить фото для заявки: '+config['last_cmd'].split(':')[1])
    except Exception as e:
        logger.error("mrmsupport_bot_test. photo: "+str(message.from_user.id)+" "+str(e))
        bot.reply_to(message, 'Не удалось загрузить фото для заявки: '+config['last_cmd'].split(':')[1])


def mrm_support_text(message, bot, logger, data_path, clientPath, row_width, max_buttons_per_page):
    # Return if it is a group
    if message.chat.type != 'private':
        return
    # Create folder if not exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    if message.text == 'Скачать приложение' and message.chat.type != 'group' and message.chat.type != 'supergroup':
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
        bot.reply_to(message, 'Скачать приложение можно по ссылке:\n'+apk_link)

    if message.text == 'Заявки' and message.chat.type != 'group' and message.chat.type != 'supergroup':
        logger.info("mrmsupport_bot_test. bidlist: "+str(message.from_user.id))
        try:
            conf_path = data_path+'user_conf/'
            # Create folder if not exists
            if not os.path.exists(conf_path):
                os.makedirs(conf_path)
            config = read_config(conf_path, message.from_user.id)
            
            # Define the maximum number of buttons per page
            # Load bid list
            # options = ['pl'+str(i) for i in range(1, 32)]
            options = bid_list(message.from_user.id, clientPath, logger)
            # options = []
            # Save bid list to config
            config['bid_list'] = options
            
            if len(options) == 0:
                bot.reply_to(message, 'Список заявок пуст')
                return

            current_page = 1
            logger.info("mrmsupport_bot_test. bidlist. current_page: "+str(current_page))
            # Calculate the total number of pages
            total_pages = ceil(len(options) / max_buttons_per_page)
            # Calculate the start and end index of the current page
            start_index = (current_page - 1) * max_buttons_per_page
            end_index = min(start_index + max_buttons_per_page, len(options))
            # Create the list of buttons for the current page
            buttons = []
            for i in range(start_index, end_index):
                button = types.InlineKeyboardButton(options[i]['id'], callback_data='bid:'+options[i]['id'])
                buttons.append(button)

            """ if len(buttons) == 0:
                bot.reply_to(message, 'Нет заявок, доступных для загрузки фото')
                return"""
            # Create the list of navigation buttons
            navigation_buttons = []
            if current_page > 1:
                navigation_buttons.append(types.InlineKeyboardButton('<', callback_data='btn:<'))
            if current_page < total_pages:
                navigation_buttons.append(types.InlineKeyboardButton('>', callback_data='btn:>'))
            # Combine the buttons into a keyboard markup
            keyboard = types.InlineKeyboardMarkup(row_width=row_width)
            keyboard.add(*buttons)
            keyboard.add(*navigation_buttons)

            config['last_cmd'] = 'bid_list'
            logger.info("mrmsupport_bot_test. b. last_cmd: "+str(config['last_cmd']))
            config['bid_list_page'] = current_page
            save_config(conf_path, config, message.from_user.id)

            # Send the message with the keyboard
            bot.send_message(chat_id=message.chat.id, text='Список заявок ['+str(current_page)+'/'+str(total_pages)+']:', reply_markup=keyboard)

            
        except Exception as e:
            logger.error(e)
            bot.reply_to(message, 'Сервис временно недоступен')

def mrm_support_bot_button_handler(call, bot, logger, data_path, row_width, max_buttons_per_page):
    try:
        # Return if it is a group
        if call.message.chat.type != 'private':
            return
        # Create folder if not exists
        if not os.path.exists(data_path):
            os.makedirs(data_path)
        conf_path = data_path+'user_conf/'
        # Create folder if not exists
        if not os.path.exists(conf_path):
            os.makedirs(conf_path)
        config = read_config(conf_path, call.from_user.id)

        # Define the maximum number of buttons per page
        options = config['bid_list']
        current_page = int(config['bid_list_page'])
        total_pages = ceil(len(options) / max_buttons_per_page)

        if call.data == 'btn:<':
            current_page -= 1
            if current_page < 1:
                current_page = 1
        elif call.data == 'btn:>':
            current_page += 1
            if current_page > total_pages:
                current_page = total_pages

        # Button: bid
        elif call.data.startswith('bid:'):
            option = call.data.split(':')[1]
            config['last_cmd'] = 'bid:'+option
            save_config(conf_path, config, call.from_user.id)

            buttons = []
            buttons.append(types.InlineKeyboardButton('Загрузить фото', callback_data='upload_photo:'+option))
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(*buttons)

            # Load bid address from config
            bid_address = ''
            for bid in config['bid_list']:
                if bid['id'] == option:
                    bid_address = str(bid['address']['city'])
                    break
            
            # bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Заявка: '+option+'\n'+bid_address, reply_markup=keyboard)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Заявка: '+option, reply_markup=keyboard)
            return

        # Button: upload photo
        elif call.data.startswith('upload_photo:'):
            config['last_cmd'] = call.data
            save_config(conf_path, config, call.from_user.id)
            logger.info("mrmsupport_bot_test. u. last_cmd: "+str(config['last_cmd']))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Пожалуйста, загрузите фото без сжатия')
            return
        else:
            option_index = int(call.data)
            option = options[option_index]
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='You chose "{}"'.format(option))
            return
        
        # Calculate the start and end index of the current page
        start_index = (current_page - 1) * max_buttons_per_page
        end_index = min(start_index + max_buttons_per_page, len(options))
        # Create the list of buttons for the current page
        buttons = []
        for i in range(start_index, end_index):
            button = types.InlineKeyboardButton(options[i]['id'], callback_data='bid:'+options[i]['id']) # TODO: Check the bid availability for this user
            buttons.append(button)
        # Create the list of navigation buttons
        navigation_buttons = []
        if current_page > 1:
            navigation_buttons.append(types.InlineKeyboardButton('<', callback_data='btn:<'))
        if current_page < total_pages:
            navigation_buttons.append(types.InlineKeyboardButton('>', callback_data='btn:>'))
        # Update the current page number in the user configuration file
        config['last_cmd'] = 'bid_list'
        # logger.info("mrmsupport_bot_test. a. last_cmd: "+str(config['last_cmd']))
        config['bid_list_page'] = current_page
        save_config(conf_path, config, call.from_user.id)        
        # Combine the buttons into a keyboard markup
        keyboard = types.InlineKeyboardMarkup(row_width=row_width)
        keyboard.add(*buttons)
        keyboard.add(*navigation_buttons)
        # Send the message with the keyboard
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Список заявок ['+str(current_page)+'/'+str(total_pages)+']:', reply_markup=keyboard)

    except Exception as e:
        logger.error(e)
        bot.reply_to(call.message, str(e))

def mrm_support_redirect(message, bot, logger, clientPath):
    try:
        logger.info('call mrm_support_redirect')
        granted_chats = [
            '-1001853379941', # MRM master info МРМ мастер, 
            '-1001533625926' # Bot factory 2
        ] 

        logger.info("Who send: "+str(message.from_user))
        logger.info('Current group: ' + str(message.chat))
        logger.info('Pervious user: ' + str(message.forward_from))
        if str(message.chat.id) in granted_chats:
            logger.info(str(message.chat.id)+' in granted_chats')
            if message.forward_from is not None:
                logger.info('Received redirect from user id: '+str(message.forward_from.id))
                reply = '[\n'
                results = mrmsupport_bot_user_info(message.forward_from.id, clientPath, logger)
                
                if len(results) == 0:
                    reply = 'User not found'
                    logger.info(reply)
                    bot.reply_to(message, reply)
                else:
                    reply += ',\n'.join(results)
                    bot.reply_to(message, reply + '\n]')
                    logger.info('Replying in '+str(message.chat.id))
            else:
                text_to_reply = 'forward_from is '+str(message.forward_from)
                logger.info(text_to_reply)
                bot.reply_to(message, text_to_reply)
    except Exception as e:
        logger.error(''+str(e))