from flask import Flask, request, jsonify, Response
# from asyncio.log import logger
# from aiohttp import web
import os
import json
import openai
from datetime import datetime as dt
import logging
import matplotlib.pyplot as plt
import os
import csv
import ast
import datetime
import json


# init logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)


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


def authenticate(user_id):
    message = ''
    # User exist if config file exist
    conf_path = 'user_conf/'
    if os.path.exists(conf_path+str(user_id)+'.json'):        
        return True, message
    else:
        message = "Для доступа к сервису, пожалуйста, перешлите это сообщение @format37\nВаш ID: `"+str(user_id)+"`"
        return False, escape_characters(message)


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


def openai_conversation(config, user_id, user_text):
    # openai conversation
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' openai conversation')
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


def reset_prompt(user_id):
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' reset_prompt')
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


####################
# Call functions:
####################
@app.route("/test")
def call_test():
    return "get ok"


@app.route("/reset", methods=["POST"])
def call_reset():
    # print('call_reset_p')
    # logger.info('call_reset')
    """request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)"""
    r = request.get_json()
    data = json.loads(r)
    user_id = str(data['user_id'])
    # logger.info(str(dt.now())+' '+'User: '+str(user_id)+' call_reset')
    
    authentication, message = authenticate(user_id)
    if not authentication:
        logger.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
        # return web.Response(text=message, content_type="text/html")
        # return jsonify({'text': message})
        return jsonify({"result": message})
    
    reset_prompt(user_id)
    # return web.Response(text='Память очищена', content_type="text/html")
    """result = jsonify({'result': 'Память очищена'})
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' reset: '+str(result))
    return result"""
    return jsonify({"result": 'Память очищена'})


@app.route("/message", methods=["POST"])
def call_message():
    """request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)"""
    r = request.get_json()
    data = json.loads(r)
    user_id = str(data['user_id'])
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' call_regular_message')
    authentication, message = authenticate(user_id)
    if not authentication:
        logger.info(str(dt.now())+' '+'User: '+str(user_id)+' not authenticated. message: '+str(message))
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
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' call_regular_message answer: '+str(answer))
    # dtype
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' call_regular_message answer type: '+str(type(answer)))
    return web.Response(text=escape_characters(answer), content_type="text/html")


@app.route("/user_add", methods=["POST"])
def call_user_add(request):
    """request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)"""
    r = request.get_json()
    data = json.loads(r)
    user_id = str(data['user_id'])
    new_user_id = str(data['new_user_id'])
    new_user_name = str(data['new_user_name'])
    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' call_user_add: '+str(new_user_id)+' '+str(new_user_name))
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


@app.route("/financial_report", methods=["POST"])
def call_financial_report(request):
    """request_str = json.loads(str(await request.text()))
    data = json.loads(request_str)"""
    r = request.get_json()
    data = json.loads(r)
    user_id = str(data['user_id'])
    count_of_days = int(data['count_of_days'])

    logger.info(str(dt.now())+' '+'User: '+str(user_id)+' call_financial_report: '+str(count_of_days))
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
                    
                    logger.info('row[2] value: '+str(row[2]))
                    logger.info('row[2] type: '+str(type(row[2])))
                    # Evaluate token count and calculate funds
                    try:
                        token_count = len(ast.literal_eval(row[2]))
                    except Exception as e:
                        logger.info('token calculation error. Exception: '+str(e))
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


"""def main():
    app = web.Application(client_max_size=1024**3)
    app.router.add_route('POST', '/regular_message', call_regular_message)
    app.router.add_route('POST', '/user_add', call_user_add)
    app.router.add_route('POST', '/financial_report', call_financial_report)
    app.router.add_route('POST', '/reset_prompt', call_reset_prompt)
    logger.info(str(dt.now())+' '+'Server started')
    web.run_app(app, port=os.environ.get('PORT', ''))


if __name__ == "__main__":
    main()
"""

if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        debug=True,
        port=int(os.environ.get("PORT", os.environ.get('PORT', '')))
        )