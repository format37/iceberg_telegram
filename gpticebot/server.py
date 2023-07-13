from asyncio.log import logger
from aiohttp import web
import os
import uuid
import asyncio
import wave
import websockets
import json
import openai
import requests
from datetime import datetime as dt
import logging
import matplotlib.pyplot as plt
import os
import csv
import ast
import datetime
import json


# enable logging
logging.basicConfig(level=logging.INFO)


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


def accept_feature_extractor(phrases, accept):
    if len(accept) > 1 and accept['text'] != '':
        accept_text = str(accept['text'])
        conf_score = []
        for result_rec in accept['result']:
            conf_score.append(float(result_rec['conf']))
        conf_mid = str(sum(conf_score)/len(conf_score))
        phrases.append(accept_text)


"""async def stt(uri, file_name, language_code):
    with open(file_name, 'rb') as f:
        r = requests.post(uri, files={'file': f}, data={'language_code': language_code})
    logger.info('stt: '+r.text)
    return r.text"""

def language_parameters(config):
    # Define the language code and name of the voice
    language_code = 'English'
    model = 'en-US-Neural2-F'
    language = config['language']
    data_path = 'data/'
    with open(data_path+'languages.json', 'r') as f:
        languages = json.load(f)
    for language in languages.values():
        if language['name'] == config['language']:
            language_code = language['code']
            model = language['female_model']
            break
    return language_code, model

def tts(tts_text, filename, config):
    tts_server = os.environ.get('TTS_SERVER', '')
    # https://cloud.google.com/text-to-speech/docs/voices
    # https://cloud.google.com/text-to-speech
    
    language_code, model = language_parameters(config)
    logger.info('tts: '+tts_text+'\n'+language_code+' '+model)
    
    data = {
        'text':tts_text,
        'language':language_code,
        'model':model,
        'speed':1.5
    }
    response = requests.post(tts_server+'/inference', json=data)
    # Save response as audio file
    with open(filename+".wav", "wb") as f:
        f.write(response.content)


def text_chat_gpt(prompt):
    openai.api_key = os.getenv("PHRASE_SEED")
    answer = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo",
        # model = 'gpt-4-32k-0314',
        model = 'gpt-4',
        messages=prompt
    )
    return answer


def load_default_config(user_id):
    conf_path = 'user_conf/'
    with open(conf_path+'config.json', 'r') as f:
        config = json.load(f)
    
    return config


def read_config(user_id):
    conf_path = 'user_conf/'
    # if user.json conf not in user_conf folder, create it
    # default config file: config.json
    if not os.path.exists(conf_path+user_id+'.json'):
        config = load_default_config(user_id)
    else:
        with open(conf_path+user_id+'.json', 'r') as f:
            config = json.load(f)
    logger.info('read_config: '+str(config))
    return config


def save_config(config, user_id):
    # user configuration
    conf_path = 'user_conf/'
    # save config
    with open(conf_path+user_id+'.json', 'w') as f:
        json.dump(config, f)


async def call_show_prompt(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_show_prompt')
    # read prompt from user config
    config = read_config(user_id)
    config['last_cmd'] = 'show_prompt'
    save_config(config, user_id)
    # content = str(config['prompt'])
    content = str(config['chat_gpt_prompt'][-1]['content'])
    return web.Response(text=content, content_type="text/html")


def reset_prompt(user_id):
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' reset_prompt')
    # read default prompt
    config = read_config(user_id)
    # init_prompt = config['init_prompt']
    chat_gpt_init_prompt = config['chat_gpt_init_prompt']
    total_tokens = config['total_tokens']
    language = config['language']
    name = config['name']
    # names = config['names']
    config = load_default_config(user_id)
    config['total_tokens'] = total_tokens
    # config['prompt'] = init_prompt
    # config['init_prompt'] = init_prompt
    config['chat_gpt_prompt'] = chat_gpt_init_prompt
    config['chat_gpt_init_prompt'] = chat_gpt_init_prompt
    config['language'] = language
    config['name'] = name
    # config['names'] = names
    config['last_cmd'] = 'reset_prompt'
    config['conversation_id'] = int(config['conversation_id']) + 1
    save_config(config, user_id)


async def call_reset_prompt(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    
    authentication, message = authenticate(user_id)
    if not authentication:
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        return web.Response(text=message, content_type="text/html")
    
    reset_prompt(user_id)
    return web.Response(text='Память очищена', content_type="text/html")


async def call_set_prompt(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_set_prompt')

    authentication, message = authenticate(user_id)
    if not authentication:
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        return web.Response(text=message, content_type="text/html")
    
    # read prompt from user config
    config = read_config(user_id)
    # set new prompt
    # config['prompt'] = data['prompt']
    config['last_cmd'] = 'set_prompt'
    save_config(config, user_id)
    return web.Response(text='Please, send me a new init prompt', content_type="text/html")

async def call_last_message(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_last_message')
    
    authentication, message = authenticate(user_id)
    if not authentication:
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        return web.Response(text=message, content_type="text/html")
    
    # read prompt from user config
    config = read_config(user_id)
    # Read last message from prompt
    last_message = config['chat_gpt_prompt'][-1]['content']    
    return web.Response(text=last_message, content_type="text/html")


async def call_update_settings(request):
    try:
        request_str = json.loads(str(await request.text()))
        data = json.loads(request_str)
        user_id = str(data['user_id'])
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' update_settings')
        # read prompt from user config
        config = read_config(user_id)
        # set new prompt
        # config['prompt'] = data['prompt']
        # config['last_cmd'] = 'set_prompt'
        """for key in data['config']:
            logger.info(str(key)+': '+str(data['config'][key]))
            config[key] = data['config'][key]"""
        for key, value in data['config'].items():
            logger.info(str(key)+': '+str(value))
            config[key] = value
        save_config(config, user_id)
        return web.Response(text='Ok', content_type="text/html")
    except Exception as e:
        logger.error(e)
        return web.Response(text='Error', content_type="text/html")


def authenticate(user_id):
    message = ''
    # User exist if config file exist
    conf_path = 'user_conf/'
    if os.path.exists(conf_path+str(user_id)+'.json'):        
        return True, message
    else:
        message = "Для доступа к сервису, пожалуйста, перешлите это сообщение @format37\nВаш ID: `"+str(user_id)+"`"
        return False, escape_characters(message)


async def call_regular_message(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_regular_message')
    authentication, message = authenticate(user_id)
    if not authentication:
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        # message = 'no'
        return web.Response(text=message, content_type="text/html")
    # read prompt from user config
    config = read_config(user_id)

    answer = 'Regular messsage received'

    if config['last_cmd'] == 'set_prompt':
        config['chat_gpt_prompt'][0]['content'] = data['message']
        config['last_cmd'] = 'regular_message'
        answer = 'Prompt set successfull'
    elif config['last_cmd'] == 'choose_language':
        config['language'] = data['message']
        config['last_cmd'] = 'regular_message'
        answer = 'Current language: '+str(config['language'])
    else:
        config['last_cmd'] = 'regular_message'
        if int(config['total_tokens']) < 0:
            answer = openai_conversation(config, user_id, data['message'])
        else:
            answer = 'Not enough funds. Please, refill your account'
    
    save_config(config, user_id)
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_regular_message answer: '+str(answer))
    # dtype
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_regular_message answer type: '+str(type(answer)))
    return web.Response(text=escape_characters(answer), content_type="text/html")


def openai_conversation(config, user_id, user_text):
    # openai conversation
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' openai conversation')
    # init
    chat_gpt_prompt = config['chat_gpt_prompt']
    chat_gpt_prompt.append({"role": "user", "content": str(user_text)})
    openai_response = text_chat_gpt(chat_gpt_prompt)
    bot_text = openai_response['choices'][0]['message']['content']
    chat_gpt_prompt.append({"role": "assistant", "content": bot_text})
    config['chat_gpt_prompt'] = chat_gpt_prompt
    total_tokens = openai_response['usage']['total_tokens']
    config['total_tokens'] = int(config['total_tokens'])+int(total_tokens)
    conversation_id = str(config['conversation_id'])

    # save config
    save_config(config, user_id)

    # append conversation_id, datetime and prompt to logs/prompt_[iser_id].csv
    # splitter is ;
    with open('logs/prompt_'+user_id+'.csv', 'a') as f:
        f.write(str(dt.now())+';'+conversation_id+';'+str(chat_gpt_prompt)+';'+str(total_tokens)+'\n')

    return str(bot_text)


async def call_voice(request):
    logging.info(str(dt.now())+' '+'call_voice')
    # return web.Response(text='x', content_type="text/html")
    # get user_id and voice file from post request
    reader = await request.multipart()
    
    # read user_id
    field = await reader.next()
    user_id = await field.read()
    # convert bytearray to text
    user_id = user_id.decode('utf-8')

    authentication, message = authenticate(user_id)
    if not authentication:
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        # message = 'no'
        return web.Response(text=message, content_type="text/html")
    
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_voice')
    
    config = read_config(user_id)

    # Read accepted users list from text file
    #granted_users = []
    #with open('granted_users.txt', 'r') as f:
    #    for line in f:
    #        granted_users.append(line.strip())

    
    # Check is user id in accepted users
    # if user_id in granted_users:

    # check user balance
    if int(config['total_tokens']) < 0:

        # generate a random token for the filename
        filename = str(uuid.uuid4())
        
        # read voice file
        field = await reader.next()        
        voice = await field.read()
        # save voice file
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_voice.save voice file')
        with open(filename+'.ogg', 'wb') as new_file:
            new_file.write(voice)
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_voice.convert to wav')
        # convert to wav
        # os.system('ffmpeg -i '+filename+'.ogg -ac 1 -ar 16000 '+filename+'.wav -y')
        
        # transcribe and receive response
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_voice.transcribe and receive response')
        stt_url = os.environ.get('STT_SERVER', '')+'/inference'
        # user_text = await stt(stt_uri+'/inference', filename+'.wav')
        # with open(file_path, 'rb') as f:
        #     r = requests.post(stt_url, files={'file': f})
        # r = requests.post(uri, files={'file': f}, data={'language_code': language_code})
        # language_code = 'en-US'
        language_code, model = language_parameters(config)
        r = requests.post(stt_url, files={'file': voice}, data={'language_code': language_code})
        # r = await stt(stt_url, filename+'.ogg', 'en-US')
        user_text = r.text

        # remove ogg file
        os.remove(filename+'.ogg')

        # safe
        #if len(config['prompt']) > 1500:
        #    #config = load_default_config(user_id)
        #    reset_prompt(user_id)

        bot_text = openai_conversation(config, user_id, user_text)

        # remove user's voice wav file
        # os.remove(filename+'.wav')

        # synthesis text to speech
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_voice.synthesis text to speech')
        tts(bot_text, filename, config)
        file_should_be_removed = True
    else:
        filename = 'data/add_funds'
        file_should_be_removed = False

    # read audio file
    with open(filename+'.wav', 'rb') as f:
        content = f.read()

    if file_should_be_removed:
        # remove synthesis wav file
        os.remove(filename+'.wav')
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_voice.response')
    return web.Response(body=content, content_type="audio/wav")


async def call_check_balance(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_check_balance')
    
    authentication, message = authenticate(user_id)
    if not authentication:
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        return web.Response(text=message, content_type="text/html")
    
    # read prompt from user config
    config = read_config(user_id)
    total_tokens = int(config['total_tokens'])
    price = float(config['price'])
    balance = -total_tokens/1000*price
    # round
    balance = round(balance, 2)
    content = '$'+str(balance)+'\nДля пополнения обратитесь к @format37'
    return web.Response(text=content, content_type="text/html")


async def call_user_add(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    new_user_id = str(data['new_user_id'])
    new_user_name = str(data['new_user_name'])
    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_user_add: '+str(new_user_id)+' '+str(new_user_name))
    # Check is user_id in admins.txt
    with open('data/admins.txt', 'r') as f:
        admins = f.read().splitlines()
    if user_id in admins:
        # add new user
        config = read_config(new_user_id)
        config['name'] = new_user_name
        save_config(config, new_user_id)
        content = 'Пользователь '+str(new_user_id)+' '+str(new_user_name)+' добавлен'
    else:
        content = 'Нет доступа'
    return web.Response(text=content, content_type="text/html")


async def call_financial_report(request):
    request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)
    user_id = str(data['user_id'])
    count_of_days = int(data['count_of_days'])

    logging.info(str(dt.now())+' '+'User: '+str(user_id)+' call_financial_report: '+str(count_of_days))
    # Check is user_id in admins.txt
    with open('data/admins.txt', 'r') as f:
        admins = f.read().splitlines()
    if user_id in admins:
        # Report
        logs_path = 'logs/'
        usernames_path = 'user_conf'
        # Create a dictionary to map user IDs to real names
        user_names = {}
        for filename in os.listdir(usernames_path):
            if filename=='config.json':
                continue
            with open(os.path.join(usernames_path, filename), 'r') as f:
                # print(os.path.join(usernames_path, filename))
                data = json.load(f)
                user_id = filename.split('.')[0]
                user_id = ''.join(filter(str.isdigit, user_id))
                user_names[user_id] = data['name']

        # Initialize empty dictionary for each user
        users_funds = {}

        # Calculate date N days ago
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=count_of_days)

        # Loop through all CSV files
        for filename in os.listdir(logs_path):
            
            if not '.csv' in filename:
                continue
            
            
                
            # Extract user ID from filename
            user_id = filename.split('.')[0]
            user_id = ''.join(filter(str.isdigit, user_id))
            # Get the real name of the user
            if user_id in user_names:
                user_name = user_names[user_id]
            else:
                user_name = user_id
            
            with open(os.path.join(logs_path, filename), newline='') as csvfile:
                
                reader = csv.reader(csvfile, delimiter=';')
                for row in reader:
                    # Parse timestamp and extract date
                    timestamp = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')
                    date = timestamp.strftime('%Y-%m-%d')
                    
                    # Extract date from filename
                    # date_str = filename.split('.')[0]
                    # date = datetime.datetime.strptime(date_str, '%Y-%m-%d')

                    # Skip files that are older than N days
                    # if date < cutoff_date:
                    #     continue
                    if count_of_days > 0 and datetime.datetime.strptime(date, '%Y-%m-%d') < cutoff_date:
                        continue
                    
                    logging.info('row[2] value: '+str(row[2]))
                    logging.info('row[2] type: '+str(type(row[2])))
                    # Evaluate token count and calculate funds
                    try:
                        token_count = len(ast.literal_eval(row[2]))
                    except Exception as e:
                        logging.info('token calculation error. Exception: '+str(e))
                        token_count = 1000
                    funds = token_count * 0.02 / 1000
                    
                    # Append funds to corresponding user's list for this date
                    if date not in users_funds:
                        users_funds[date] = {}
                    if user_name not in users_funds[date]:
                        users_funds[date][user_name] = 0
                    users_funds[date][user_name] += funds

        # Prepare data for plotting
        user_names_sorted = sorted(list(set([user_name for date in users_funds for user_name in users_funds[date]])))
        dates = sorted(list(users_funds.keys()))
        funds_by_user_and_date = [[users_funds[date].get(user_name, 0) for date in dates] for user_name in user_names_sorted]

        # Plot stacked bar chart
        fig, ax = plt.subplots()
        ax.bar(dates, funds_by_user_and_date[0], label=user_names_sorted[0])
        bottom = funds_by_user_and_date[0]
        for i in range(1, len(user_names_sorted)):
            ax.bar(dates, funds_by_user_and_date[i], bottom=bottom, label=user_names_sorted[i])
            bottom = [bottom[j] + funds_by_user_and_date[i][j] for j in range(len(dates))]

        # Add chart labels and legend
        plt.xlabel('Date')
        plt.ylabel('Funds Spent (USD)')
        plt.title('Funds Spent by User and Date')
        plt.legend()

        # Save chart to image file
        plt.savefig('funds_spent.png')
        # content = 'Отчет сформирован'
        
        # Return image file
        with open('funds_spent.png', 'rb') as f:
            content = f.read()
        return web.Response(body=content, content_type='image/png')
    
    else:
        content = 'Нет доступа'
    return web.Response(text=content, content_type="text/html")


async def call_inline(request):
    r = await request.json()
    # logger.info("request data: {}".format(r))
    # Assuming r is a JSON-formatted string
    r_dict = json.loads(r)
    user_id = r_dict["user_id"]
    # logger.info("user_id: {}".format(user_id))
    # Read userlist from data/users.txt
    """with open("data/access.txt", "r") as f:
        userlist = f.read().splitlines()
    # replace new line
    userlist = [int(x) for x in userlist]"""
    authentication, result = authenticate(user_id)
    if not authentication:
        # message = 'Доступа нет'
        logging.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(result))
        # message = 'no'
        # return web.Response(text=message, content_type="text/html")
    else:
    
        # if user_id in userlist:
        # if True:
        config = read_config(user_id)
        logger.info("inline query: {}".format(r_dict["query"]))
        query = r_dict["query"]
        openai.api_key = os.getenv("PHRASE_SEED")
        answer = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "system", "content": config['chat_gpt_prompt']},
                {"role": "user", "content": str(query)}
            ]
        )
        logger.info("answer: {}".format(answer))
        result = answer['choices'][0]['message']['content']

    """else:
        logger.info("User not allowed: {}".format(user_id))
        result = "You are not allowed to access this service"
    """
    # return jsonify({"result": result})
    return web.json_response({"result": result})


def main():
    app = web.Application(client_max_size=1024**3)
    app.router.add_route('POST', '/voice_message', call_voice)
    app.router.add_route('POST', '/show_prompt', call_show_prompt)
    app.router.add_route('POST', '/reset_prompt', call_reset_prompt)
    app.router.add_route('POST', '/set_prompt', call_set_prompt)
    app.router.add_route('POST', '/regular_message', call_regular_message)
    app.router.add_route('POST', '/check_balance', call_check_balance)
    app.router.add_route('POST', '/update_settings', call_update_settings)
    app.router.add_route('POST', '/last_message', call_last_message)
    app.router.add_route('POST', '/inline', call_inline)
    app.router.add_route('POST', '/user_add', call_user_add)
    app.router.add_route('POST', '/financial_report', call_financial_report)
    logging.info(str(dt.now())+' '+'Server started')
    web.run_app(app, port=os.environ.get('PORT', ''))


if __name__ == "__main__":
    main()
