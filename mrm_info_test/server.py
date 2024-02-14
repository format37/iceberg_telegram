from fastapi import FastAPI, Request, HTTPException
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


# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TextOutput(BaseModel):
    text: str = Field(description="Text output")

class BotActionType(BaseModel):
    val: str = Field(description="Tool parameter value")

class ChatAgent:
    def __init__(self, retriever):
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # self.config = bot_instance.config
        self.config = {
            # 'model': 'gpt-4-0125-preview',
            'model': 'gpt-3.5-turbo',
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
        # llm = Ollama(model="llama2")
        # llm = Ollama(model="mistral")
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
        """tools.append(
            Tool(
                args_schema=DocumentInput,
                name='Knowledge base',
                description="Providing a game information from the knowledge base",
                func=RetrievalQA.from_chain_type(llm=llm, retriever=self.retriever),
            )
        )"""
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


def mrmsupport_bot_user_info(user_id, clientPath):
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

    granted_chats = [
        '-1001853379941', # MRM master info МРМ мастер, 
        '-1002094333974', # botchat (test)
        '-1002087087929' # TehPodMRM Comments
    ]

    answer = "Система временно находится на техническом обслуживании. Приносим извенение за доставленные неудобства."

    if str(message['chat']['id']) in granted_chats and 'forward_origin' in message:
        logger.info(str(message['chat']['id'])+' in granted_chats')
        results = []
        # if message.forward_from is not None:
        if 'forward_from' in message:
            # logger.info('Received redirect from user id: '+str(message.forward_from.id))
            logger.info('Received redirect from user id: '+str(message['forward_from']['id']))
            reply = '[\n'
            # results = mrmsupport_bot_user_info(message.forward_from.id, clientPath)
            results = mrmsupport_bot_user_info(message['forward_from']['id'], clientPath)
        else:
            results.append('User not found')

        # Get the Langchain LLM opinion
        chat_history = []
        retriever = None
        
        message_text = f"""Received a message from mobile application user:
"{message['text']}"
Please, use your knowledge database to provide your thoughts on the issue,
recommendations for technical support team, and answer to user.
Provide your answer as JSON structure: "thoughts", "tech_recommendations", "answer_for_user"."""
        # TODO: Add user technical information to the message_text
        message_text = message_text.replace('\n', ' ')
        chat_agent = ChatAgent(retriever)
        response = chat_agent.agent.run(
            input=message_text, 
            chat_history=chat_history
        )
        results.append(response)
        
        """if len(results) == 0:
            answer = 'User not found'
            logger.info(answer)
        else:"""
        reply += ',\n'.join(results)
        answer = reply + '\n]'
        # logger.info('Replying in '+str(message.chat.id))
        logger.info('Replying in '+str(message['chat']['id']))
        """else:
            answer = 'Unable to retrieve the hidden user id'
            logger.info(answer)"""
    else:
        return JSONResponse(content={
                "type": "empty",
                "body": ""
                })

    return JSONResponse(content={
        "type": "text",
        "body": str(answer)
        })
