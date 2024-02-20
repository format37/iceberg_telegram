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
    
document_processor = DocumentProcessor(context_path='/server/data/')
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
            'model': 'gpt-4-0125-preview',
            # 'model': 'gpt-3.5-turbo',
            'temperature': 0.7,
        }
        self.retriever = retriever
        # self.bot_instance = bot_instance  # Passing the Bot instance to the ChatAgent
        # self.logger.info(f"ChatAgent function: {self.bot_instance.bot_action_come}")
        self.agent = self.initialize_agent()
        

    def initialize_agent(self):
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
        return initialize_agent(
            tools,
            llm,
            agent='chat-conversational-react-description',
            verbose=True,
            handle_parsing_errors=True
        )
    


    @staticmethod
    def create_structured_tool(func, name, description, return_direct):
        print(f"create_structured_tool name: {name} func: {func}")
        return StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            args_schema=BotActionType,
            return_direct=return_direct,
        )


@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})


def mrmsupport_bot_user_info(user_id):
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


@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
# async def call_message(request: Request):

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
    
    if 'forward_origin' in message:
        logger.info(str(message['chat']['id'])+' in granted_chats')
        results = []
        if 'forward_from' in message:
            logger.info('Received redirect from user id: '+str(message['forward_from']['id']))
            reply = '[\n'
            results = mrmsupport_bot_user_info(message['forward_from']['id'])
        else:
            results.append('User id is hidden')

        # Before joining the results, convert each item to a string if it's not already one
        results_as_strings = [json.dumps(item) if isinstance(item, dict) else str(item) for item in results]
        # Now you can safely join the string representations of your results
        reply += ',\n'.join(results_as_strings)
        answer = reply + '\n]'
        bot = telebot.TeleBot(token)
        bot.send_message(message['chat']['id'], answer)

    user_text = ''
    if 'text' in message:
        user_text += message['text']
    # TODO: Implement photo reading
        
    if user_text != '':
        # Get the Langchain LLM opinion
        chat_history = []
        # retriever = None
        # document_processor = DocumentProcessor(context_path='/server/data/')
        # retriever = document_processor.process_documents()
        
        message_text = f"""Received a support request from user: "{message['text']}"
User technical infrmation:\n"""
        message_text += str(results) if len(results) > 0 else "Not provided" # Tech info from 1C
        message_text += """\n
Please be sure to use the Retrieval search database. And then provide the answer to the user in Russian."""
        message_text = message_text.replace('\n', ' ')
        chat_agent = ChatAgent(retriever)
        answer = chat_agent.agent.run(
            input=message_text, 
            chat_history=chat_history
        )
        # logger.info(f"ChatAgent response: {response}")
        # results.append(response)
        # logger.info('Replying in '+str(message.chat.id))
        logger.info('Replying in '+str(message['chat']['id']))
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })

    return JSONResponse(content={
            "type": "empty",
            "body": ""
            })
