from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from config_manager import ConfigManager
from chat_history_service import ChatHistoryService
from photo_description_service import PhotoDescriptionService
from onecproxy import OneCProxyService
import telebot
import logging
import json
from langchain_community.tools import StructuredTool
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from pydantic import BaseModel, Field
from langchain.tools import Tool
from langchain.agents import initialize_agent
import os
from langchain.chains import RetrievalQA
import uvicorn

class DocumentProcessor:
    def __init__(self, context_path):
        self.context_path = context_path

    def process_documents(self, logger):
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
    

class TextOutput(BaseModel):
    text: str = Field(description="Text output")

class BotActionType(BaseModel):
    val: str = Field(description="Tool parameter value")

class DocumentInput(BaseModel):
    question: str = Field()

class ChatAgent:
    def __init__(self, retriever, model, temperature):
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # self.config = bot_instance.config
        self.config = {
            'model': model,
            'temperature': temperature
            # 'gpt-4-0125-preview',
            # 'model': 'gpt-3.5-turbo', # test
            # 'temperature': 0.6,
        }
        self.retriever = retriever
        self.agent = None        

    async def initialize_agent(self):
        llm = ChatOpenAI(
            openai_api_key=os.environ.get('OPENAI_API_KEY', ''),
            model=self.config['model'],
            temperature=self.config['temperature'],
        )
        tools = []
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


class Application:
    def __init__(self):
        self.config_manager = ConfigManager('config.json')
        self.logger = self.setup_logging()
        self.chat_history_service = ChatHistoryService(
            self.config_manager.get("chats_dir"),
            self.logger
            )
        self.photo_description_service = PhotoDescriptionService(
            self.config_manager.get("temp_dir"), 
            self.config_manager.get("api_key"),
            self.logger
            )
        self.onec_service = OneCProxyService(
            self.config_manager.get("onec_base_url"),
            self.logger
            )
        
        self.app = FastAPI()
        self.setup_routes()
        
        self.document_processor = DocumentProcessor(
            context_path=self.config_manager.get("retrieval_dir")
            )
        self.retriever = self.document_processor.process_documents(self.logger)

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        return logger

    def setup_routes(self):
        @self.app.post("/message")
        async def handle_message(request: Request, authorization: str = Header(None)):
            self.logger.info('handle_message')
            message = await request.json()
            self.logger.info(message)

            token = None
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
            
            if token:
                pass
            else:
                answer = """Не удалось определить токен бота.
Пожалуйста обратитесь к администратору."""
                return JSONResponse(content={
                    "type": "text",
                    "body": str(answer)
                })

            granted_chats = [
                '-1001853379941', # MRM master info МРМ мастер, 
                '-1002094333974', # botchat (test)
                '-1002087087929' # TehPodMRM Comments
            ]
            
            answer = """Система временно находится на техническом обслуживании.
Приносим извенение за доставленные неудобства."""
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
                try:
                    description = await self.photo_description_service.get_photo_description(
                            bot, 
                            message
                            )
                    message_text += description
                    if 'text' in message:
                        message_text += '\nUser comment: '
                except Exception as e:
                    # Handle exception, perhaps log it or send a message to admin
                    print(f"Error during photo description: {e}")

            if await self.chat_history_service.is_message_deprecated(0, message, reply_to_message_id):
                return JSONResponse(content={
                    "type": "empty",
                    "body": ""
                    })

            # Save to chat history
            await self.chat_history_service.save_to_chat_history(
                message['chat']['id'],
                message_text,
                message['message_id'],
                'HumanMessage',
                message['from']['first_name'],
                '0-incoming'
            )

            if 'reply_to_message' in message:
                if 'mrminfotestbot' in message['reply_to_message']['from']['username'] or \
                    'mrminfobot' in message['reply_to_message']['from']['username']:
                    pass # Ok, we need to reply to direct message to bot
                else:
                    # Return empty
                    return JSONResponse(content={
                        "type": "empty",
                        "body": ""
                        })
            
            reply = '[\n'
            results = []
            
            if not await self.chat_history_service.configuration_in_history(reply_to_message_id):
                if 'forward_origin' in message and 'forward_from' in message:
                    results = self.onec_service.get_user_info(message['forward_from']['id'])
                else:
                    results.append('Техническая информация о пользователе недоступна')
                # Add information about the latest version of the application
                actual_version_info = self.onec_service.get_actual_version()
                
                self.logger.info(f'actual_version_info: {actual_version_info}')
                # Return empty: TODO: Remove this
                return JSONResponse(content={
                    "type": "empty",
                    "body": ""
                    })

                if len(actual_version_info) > 0:
                    new_element = {
                        'Available Update Version': actual_version_info['version'],
                        'Update link': actual_version_info['link']
                    }
                    results.append(new_element)
                # Before joining the results, convert each item to a string if it's not already one
                results_as_strings = [json.dumps(item) if isinstance(item, dict) else str(item) for item in results]
                # Now you can safely join the string representations of your results
                reply += ',\n'.join(results_as_strings)
                answer = reply + '\n]'

            # Save to chat history
            await self.chat_history_service.save_to_chat_history(
                message['chat']['id'],
                answer,
                message['message_id'],
                'AIMessage',
                message['from']['first_name'],
                '1-configuration'
            )

            bot.send_message(
                message['chat']['id'], 
                answer, 
                reply_to_message_id=message['message_id']
                )
            
            user_text = message_text
            self.logger.info(f'[4] DEBUG: User text: {user_text}')

            if await self.chat_history_service.is_message_deprecated(1, message, reply_to_message_id):
                return JSONResponse(content={
                    "type": "empty",
                    "body": ""
                    })
            
            # Read chat history in LLM fromat
            chat_history = await self.chat_history_service.read_chat_history(message['chat']['id'])
            if user_text != '':
                if await self.chat_history_service.is_message_deprecated(2, message, reply_to_message_id):
                    return JSONResponse(content={
                        "type": "empty",
                        "body": ""
                        })
                user_info = str(results) if len(results) > 0 else "Not provided" # Tech info from 1C
                message_text = f"""Вы представитель технической поддержки и разработчик Мобильного приложения мастера.
К вам поступил запрос от пользователя: "{user_text}"
Разработчик приложения уже увидел это сообщение.
Техническая информация о пользвателе:
{user_info}
Рекомендуется использовать Retrieval search database tool, если это может быть полезно в контексте запроса пользователя.
Retrieval search database содержит набор ответов на частые вопросы пользователей, а так же набор инструкций пользователя и инструкций о том как правильно вести поддержку пользователей.
Ваш ответ должен быть на русском языке.
Используйте пустые строки для разделения абзацев.
Не предлагайте связаться с технической поддержкой, вы и есть техническая поддеркжа. Вместо этого, можете предложить обращаться повторно.
Не предлагайте обновить приложение, если 'app_version' уже соответствует 'Available Update Version'.
Пожалуйста, предоставьте рекоммендации пользовтелю, как ему решить его проблему. Можете задать уточняющие вопросы если необходимо."""
                message_text = message_text.replace('\n', ' ')
                chat_agent = ChatAgent(
                    retriever=self.retriever, 
                    model=self.config_manager.get("model"), 
                    temperature=self.config_manager.get("temperature")
                    )
                await chat_agent.initialize_agent()
                answer = chat_agent.agent.run(
                    input=message_text, 
                    chat_history=chat_history
                )
                # Return empty if deprecated
                if await self.chat_history_service.is_message_deprecated(3, message, reply_to_message_id):
                    return JSONResponse(content={
                        "type": "empty",
                        "body": ""
                        })
                
                # Save to chat history
                await self.chat_history_service.save_to_chat_history(
                    message['chat']['id'],
                    answer,
                    message['message_id'],
                    'AIMessage',
                    message['from']['first_name'],
                    '9-llm'
                )

                self.logger.info('Replying in '+str(message['chat']['id']))
                self.logger.info(f'Answer: {answer}')
                return JSONResponse(content={
                    "type": "text",
                    "body": str(answer)
                })


"""if __name__ == "__main__":
    import uvicorn
    application = Application()
    uvicorn.run(application.app, host="0.0.0.0", port=8000)"""

application = Application()
app = application.app