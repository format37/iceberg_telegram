from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import os
import logging
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport

import json
import requests
# import time
import glob
import json
from pydantic import BaseModel, Field
from langchain.agents import Tool, initialize_agent
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_community.tools import StructuredTool
from langchain.schema import HumanMessage, SystemMessage, AIMessage
# from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.chains import RetrievalQA
from langchain.tools import Tool
# from langchain.schema import TextOutput
from langchain_experimental.utilities import PythonREPL
import time as py_time
from pathlib import Path
import tiktoken
import telebot
# from pydantic import BaseModel, Field
import base64
import aiofiles

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DocumentProcessor:
    def __init__(self, context_path):
        self.context_path = context_path

    def process_documents(self):
        context_path = self.context_path
        logger.info(f"Processing documents from {context_path}")
        loader = DirectoryLoader(context_path, glob="*", loader_cls=TextLoader)
        docs = loader.load()
        logger.info(f"Loaded {len(docs)} documents")
        api_key = os.environ.get('OPENAI_API_KEY', '')
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        text_splitter = RecursiveCharacterTextSplitter()
        documents = text_splitter.split_documents(docs)
        logger.info(f"Split {len(documents)} documents")
        vector = DocArrayInMemorySearch.from_documents(documents, embeddings)
        return vector.as_retriever()
    
document_processor = DocumentProcessor(context_path='/server/data/retrieval/')
retriever = document_processor.process_documents()

class TextOutput(BaseModel):
    text: str = Field(description="Text output")

class BotActionType(BaseModel):
    val: str = Field(description="Tool parameter value")

class DocumentInput(BaseModel):
    question: str = Field()

class ChatAgent:
    def __init__(self, retriever):
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # self.config = bot_instance.config
        self.config = {
            # 'model': 'gpt-4-0125-preview',
            'model': 'gpt-3.5-turbo', # test
            'temperature': 0.7,
        }
        self.retriever = retriever
        # self.bot_instance = bot_instance  # Passing the Bot instance to the ChatAgent
        # self.logger.info(f"ChatAgent function: {self.bot_instance.bot_action_come}")
        # self.agent = self.initialize_agent()
        # self.agent = await self.initialize_agent()
        self.agent = None        

    async def initialize_agent(self):
        llm = ChatOpenAI(
            openai_api_key=os.environ.get('OPENAI_API_KEY', ''),
            model=self.config['model'],
            temperature=self.config['temperature'],
        )
        tools = []
        # python_repl = PythonREPL()
        # Non direct return
        """repl_tool = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=python_repl.run,
            return_direct=False,
        )
        tools.append(repl_tool)"""
        """tools = [self.create_structured_tool(func, name, description, return_direct)
                 for func, name, description, return_direct in [
                        (self.bot_instance.web_browser_tool, "Web browsing",
                            "Provide a link to request", True)
                      ]
                 ]"""
        # embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get('OPENAI_API_KEY', ''))
        # web_browsing_tool = SimulatedWebBrowsingTool(llm, embeddings)
        # tools.append(web_browsing_tool)
        # tools.append(DuckDuckGoSearchRun())
        # tools.append(DuckDuckGoSearchResults())
        # wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
        # tools.append(wikipedia)
        tools.append(
            Tool(
                args_schema=DocumentInput,
                name='Retrieval search database',
                description="Questions, answers, instructions",
                func=RetrievalQA.from_chain_type(llm=llm, retriever=self.retriever),
            )
        )
        self.agent = initialize_agent(
            tools,
            llm,
            agent='chat-conversational-react-description',
            verbose=True,
            handle_parsing_errors=True
        )
    


    @staticmethod
    async def create_structured_tool(func, name, description, return_direct):
        print(f"create_structured_tool name: {name} func: {func}")
        return StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            args_schema=BotActionType,
            return_direct=return_direct,
        )
    
async def configuration_in_history(chat_id: str):
    data_dir = '/server/data/chats'
    chat_log_path = os.path.join(data_dir, str(chat_id))
    # Create the chat log path if not exist
    Path(chat_log_path).mkdir(parents=True, exist_ok=True)
    # self.crop_queue(chat_id=chat_id)
    logger.info(f'DEBUG: Listing chat_log_path: {chat_log_path}')
    for log_file in sorted(os.listdir(chat_log_path)):
        logger.info(f'DEBUG: log_file: {log_file}')
        # Return True if 'configuration' word is in the file_name
        if 'configuration' in log_file:
            logger.info(f'DEBUG: configuration_in_history chat_id: {chat_id} True')
            return True
    logger.info(f'DEBUG: NOT configuration_in_history chat_id: {chat_id} False')
    return False
    
async def save_to_chat_history(
        chat_id, 
        message_text, 
        message_id,
        type,
        message_date = None,
        name_of_user = 'AI',
        event_id = 'default'
        ):
    logger.info(f'save_to_chat_history chat_id: {chat_id} message_id: {message_id} type: {type} message_date: {message_date} name_of_user: {name_of_user} event_id: {event_id}')
    # Prepare a folder
    path = f'./data/chats/{chat_id}'
    os.makedirs(path, exist_ok=True)
    if message_date is None:
        message_date = py_time.strftime('%Y-%m-%d-%H-%M-%S', py_time.localtime())
    log_file_name = f'{message_date}_{message_id}_{event_id}.json'

    data_dir = '/server/data/chats'
    chat_log_path = os.path.join(data_dir, str(chat_id))
    Path(chat_log_path).mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(os.path.join(chat_log_path, log_file_name), 'w') as log_file:
        await log_file.write(json.dumps({
            "type": type,
            "text": f"{message_text}",
            "date": message_date,
            "message_id": message_id,
            "name_of_user": name_of_user
        }, ensure_ascii=False))
        
async def date_of_latest_message(message_date, chat_id: str):
    '''Reads the chat history from a folder.'''
    chat_history = []
    data_dir = '/server/data/chats'
    chat_log_path = os.path.join(data_dir, str(chat_id))
    # Create the chat log path if not exist
    Path(chat_log_path).mkdir(parents=True, exist_ok=True)
    folders = os.listdir(chat_log_path)
    if len(folders) == 0:
        logger.info(f'No chat history found for chat_id: {chat_id}')
        return message_date
    else:
        logger.info(f'Chat history for chat_id: {chat_id} is {len(folders)} messages.')
    for log_file in sorted(folders):
        with open(os.path.join(chat_log_path, log_file), 'r') as file:
            try:
                # message = json.load(file)
                # chat_history.append(message)
                # Extract date from file_name = f'{message_date}_{message_id}.json'
                chat_history.append({
                    'date': int(log_file.split('_')[0]),
                    'message_id': int(log_file.split('_')[1].split('.')[0])
                })
            except Exception as e:
                logger.info(f'Error reading chat history: {e}')
                # Remove
                os.remove(os.path.join(chat_log_path, log_file))
    return chat_history[-1]['date']
        
            
async def read_chat_history(chat_id: str):
    '''Reads the chat history from a folder.'''
    chat_history = []
    data_dir = '/server/data/chats'
    chat_log_path = os.path.join(data_dir, str(chat_id))
    # Create the chat log path if not exist
    Path(chat_log_path).mkdir(parents=True, exist_ok=True)
    # self.crop_queue(chat_id=chat_id)
    logger.info(f'[5] DEBUG: Listing chat_log_path: {chat_log_path}')
    for log_file in sorted(os.listdir(chat_log_path)):
        with open(os.path.join(chat_log_path, log_file), 'r') as file:
            try:
                message = json.load(file)
                logger.info(f'[5] DEBUG: message: {message}')
                if message['type'] == 'AIMessage':
                    chat_history.append(AIMessage(content=message['text']))
                elif message['type'] == 'HumanMessage':
                    chat_history.append(HumanMessage(content=message['text']))
            except Exception as e:
                logger.info(f'Error reading chat history: {e}')
                # Remove
                os.remove(os.path.join(chat_log_path, log_file))
    return chat_history

async def read_chat_history_as_structure(chat_id: str):
    '''Reads the chat history from a folder.'''
    chat_history = []
    data_dir = '/server/data/chats'
    chat_log_path = os.path.join(data_dir, str(chat_id))
    # Create the chat log path if not exist
    Path(chat_log_path).mkdir(parents=True, exist_ok=True)
    # self.crop_queue(chat_id=chat_id)
    for log_file in sorted(os.listdir(chat_log_path)):
        with open(os.path.join(chat_log_path, log_file), 'r') as file:
            try:
                message = json.load(file)
                chat_history.append(message)
            except Exception as e:
                logger.info(f'Error reading chat history: {e}')
                # Remove
                os.remove(os.path.join(chat_log_path, log_file))
    return chat_history


@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})


async def mrmsupport_bot_user_info(user_id):
    # Server base URL
    base_url = "https://service.icecorp.ru:7403"
    url = f"{base_url}/user_info"
    headers = {'Content-Type': 'application/json'}
    token = os.environ.get('MRMSUPPORTBOT_TOKEN', '')
    data = {
        'token': token,
        'user_id': user_id
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    logger.info(f"User Info Endpoint Response: {response}")
    if response.status_code == 200:
        return response.json()
    else:
        return []
    
async def mrmsupport_bot_actual_version():
    # Server base URL
    base_url = "https://service.icecorp.ru:7403"
    url = f"{base_url}/actual_version"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers)
    logger.info(f"Actual Version Endpoint Response: {response}")
    if response.status_code == 200:
        return response.json()
    else:
        return []
    
async def photo_description(bot, message):
    user_text = ''
    # Make dir temp if not exists
    if not os.path.exists('temp'):
        os.makedirs('temp')
    # Download photo
    file_info = bot.get_file(message['photo'][-1]['file_id'])
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = 'temp/'+str(message['photo'][-1]['file_id'])+'.jpg'
    # file_path = 'sample.jpg'
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)
    model = 'gpt-4-vision-preview'
    # Function to encode the image
    async def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    # Getting the base64 string
    base64_image = await encode_image(file_path)
    logger.info(f'base64_image file_path: {file_path} len: {len(base64_image)}')
    api_key = os.environ.get('OPENAI_API_KEY', '')
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }
    payload = {
    "model": model,
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": "Пожалуйста, опишите максимально детально, что вы видите на этом изображении?"
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 1500
    }
    logger.info(f'Posting payload..')
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_json = response.json()
    logger.info(f'response: {response_json}')
    if response.status_code == 200:            
        logger.info(f'response_json: {response_json}')
        description = response_json['choices'][0]['message']['content']
        user_text += '\nОписание скриншота, который прислал пользователь:\n'        
        user_text += description
        logger.info(f'Screenshot description:\n{description}')
    # Remove temp file
    os.remove(file_path)
    if 'caption' in message:
        user_text += '\nUser comment: '+message['caption']
    return user_text


async def message_is_deprecated(event_id, message, reply_to_message_id):
    current_date = message['date']
    latest_date = await date_of_latest_message(message['date'], reply_to_message_id)
    logger.info(f'[{event_id}] current_date: {current_date} latest_date: {latest_date}')
    if current_date < latest_date:
        logger.info(f'[{event_id}] Cancelling task: Message is not the latest')
        return True
    return False


@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):

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

    granted_chats = [
        '-1001853379941', # MRM master info МРМ мастер, 
        '-1002094333974', # botchat (test)
        '-1002087087929' # TehPodMRM Comments
    ]

    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."

    if not str(message['chat']['id']) in granted_chats:
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    if 'message_thread_id' in message:
        reply_to_message_id = message['message_thread_id']
    elif 'reply_to_message' in message and \
        'message_id' in message['reply_to_message']:
        reply_to_message_id = message['reply_to_message']['message_id']
    else:
        reply_to_message_id = message['message_id']

    message_text = ''

    bot = telebot.TeleBot(token)

    # Photo description
    if 'photo' in message:
        message_text += await photo_description(bot, message)
        if 'text' in message:
            message_text += 'User comment: '

    if 'text' in message:
        message_text += message['text']
    logger.info(f'[1] DEBUG: User message: {message_text}')

    if await message_is_deprecated(0, message, reply_to_message_id):
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })

    # Save to chat history
    await save_to_chat_history(
        reply_to_message_id, 
        message_text, 
        message['message_id'],
        'HumanMessage',
        message['date'],
        message['from']['first_name'],
        '0-incoming'
        )
    
    if 'reply_to_message' in message:
        # Return empty
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    reply = '[\n'
    results = []
    
    if not await configuration_in_history(reply_to_message_id):
        if 'forward_origin' in message and 'forward_from' in message:
            logger.info('Received redirect from user id: '+str(message['forward_from']['id']))
            results = await mrmsupport_bot_user_info(message['forward_from']['id'])
        else:
            results.append('Техническая информация о пользователе недоступна')

        # Add information about the latest version of the application
        actual_version_info = await mrmsupport_bot_actual_version()
        if len(actual_version_info) > 0:
            new_element = {
                'Available Update Version': actual_version_info['version'],
                'Update link': actual_version_info['link']
            }
            # logger.info(f'new_element: {new_element}')
            results.append(new_element)

        # Before joining the results, convert each item to a string if it's not already one
        results_as_strings = [json.dumps(item) if isinstance(item, dict) else str(item) for item in results]
        # Now you can safely join the string representations of your results
        reply += ',\n'.join(results_as_strings)
        answer = reply + '\n]'

        # Save to chat history
        await save_to_chat_history(
            reply_to_message_id, 
            answer, 
            message['message_id'],
            'AIMessage',
            message['date'],
            message['from']['first_name'],
            '1-configuration'
            )

        
        bot.send_message(
            message['chat']['id'], 
            answer, 
            reply_to_message_id=message['message_id']
            )

    """user_text = ''
    if 'text' in message:
        user_text += message['text']"""
    # Read chat history as a struct to get the latest user message
    """chat_history_struct = await read_chat_history_as_structure(reply_to_message_id)
    logger.info(f'[3] DEBUG:chat_history: {chat_history_struct}')
    if len(chat_history_struct):
        user_text = chat_history_struct[-1]['text']
    else:"""
    user_text = message_text
    logger.info(f'[4] DEBUG: User text: {user_text}')

    if await message_is_deprecated(1, message, reply_to_message_id):
        return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
    
    # Photo description
    """if 'photo' in message:
        user_text += await photo_description(bot, message)"""
    
    # Read chat history in LLM fromat
    chat_history = await read_chat_history(reply_to_message_id)
    logger.info(f'[6] DEBUG:chat_history: {chat_history}')
        
    if user_text != '':
        if await message_is_deprecated(2, message, reply_to_message_id):
            return JSONResponse(content={
                "type": "empty",
                "body": ""
                })
        # Get the Langchain LLM opinion
        # chat_history = []
        # retriever = None
        # document_processor = DocumentProcessor(context_path='/server/data/')
        # retriever = document_processor.process_documents()
        
        message_text = f"""You are mobile application suport.
You have received a support request from user: "{user_text}"
This request will be sent automatically to Developer team.
User technical infrmation:\n"""
        message_text += str(results) if len(results) > 0 else "Not provided" # Tech info from 1C
        message_text += """\n
You NEED to use the Retrieval search database tool.
This database contains significant information about user support.
Use the obtained information to provide useful solutions or recommendations to the user in Russian.
Don't recommend to call technical support because this request is already in the queue.
Don't forget to add space between paragraphs.
Пожалуйста, предоставьте рекоммендации пользовтелю на русском языке. Можете задать уточняющие вопросы если необходимо."""
        message_text = message_text.replace('\n', ' ')
        chat_agent = ChatAgent(retriever)
        await chat_agent.initialize_agent()
        answer = chat_agent.agent.run(
            input=message_text, 
            chat_history=chat_history
        )
        
        if await message_is_deprecated(3, message, reply_to_message_id):
            return JSONResponse(content={
                "type": "empty",
                "body": ""
                })
        
        # Save to chat history
        await save_to_chat_history(
            reply_to_message_id, 
            answer, 
            message['message_id'],
            'AIMessage',
            message['date'],
            message['from']['first_name'],
            '9-llm'
            )

        logger.info('Replying in '+str(message['chat']['id']))
        logger.info(f'Answer: {answer}')
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })

    return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
