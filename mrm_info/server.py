from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from config_manager import ConfigManager
from chat_history_service import ChatHistoryService
from photo_description_service import PhotoDescriptionService
from onecproxy import OneCProxyService
import telebot
import logging
import json
from langchain_environment import ChatAgent, DocumentProcessor
# import uvicorn
import os

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
            os.environ.get('OPENAI_API_KEY', ''),
            logger = self.logger
            )
        self.onec_service = OneCProxyService(
            self.config_manager.get("onec_base_url"),
            self.logger
            )
        self.empty_response = JSONResponse(content={"type": "empty", "body": ""})
        
        self.app = FastAPI()
        self.setup_routes()
        
        self.document_processor = DocumentProcessor(
            context_path=self.config_manager.get("retrieval_dir")
            )
        self.retriever = self.document_processor.process_documents(self.logger)

    def text_response(self, text):
        return JSONResponse(content={"type": "text", "body": str(text)})

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
                return self.text_response(answer)

            granted_chats = [
                '-1001853379941', # MRM master info МРМ мастер, 
                '-1002094333974', # botchat (test)
                '-1002087087929' # TehPodMRM Comments
            ]
            
            answer = """Система временно находится на техническом обслуживании.
Приносим извенение за доставленные неудобства."""
            if not str(message['chat']['id']) in granted_chats:
                return self.empty_response
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
                    self.logger.info('Photo detected, getting description...')
                    description = await self.photo_description_service.get_photo_description(
                            bot, 
                            message
                            )
                    description = str(description)
                    self.logger.info(f'Photo description: {description}')
                    message_text += description
                    if 'text' in message:
                        message_text += '\nUser comment: '
                except Exception as e:
                    # Handle exception, perhaps log it or send a message to admin
                    self.logger.info(f"Error during photo description: {e}")

            if 'text' in message:
                message_text += message['text']
            self.logger.info(f'[1] DEBUG: User message: {message_text}')

            if await self.chat_history_service.is_message_deprecated(0, message, reply_to_message_id):
                return self.empty_response

            # Save to chat history
            # message['chat']['id'],
            await self.chat_history_service.save_to_chat_history(                
                message['message_id'],
                message_text,
                message['message_id'],
                'HumanMessage',
                message['from']['first_name'],
                'incoming'
            )

            if 'reply_to_message' in message:
                if 'mrminfotestbot' in message['reply_to_message']['from']['username'] or \
                    'mrminfobot' in message['reply_to_message']['from']['username']:
                    pass # Ok, we need to reply to direct message to bot
                else:
                    # Return empty
                    return self.empty_response
            
            reply = '[\n'
            results = []
            
            if not await self.chat_history_service.configuration_in_history(reply_to_message_id):
                if 'forward_origin' in message and 'forward_from' in message:
                    results = await self.onec_service.get_user_info(message['forward_from']['id'])
                else:
                    results.append('Техническая информация о пользователе недоступна')
                # Add information about the latest version of the application
                actual_version_info = await self.onec_service.get_actual_version()

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
                'configuration'
            )

            bot.send_message(
                message['chat']['id'], 
                answer, 
                reply_to_message_id=message['message_id']
                )
            
            user_text = message_text
            self.logger.info(f'[4] DEBUG: User text: {user_text}')

            if await self.chat_history_service.is_message_deprecated(1, message, reply_to_message_id):
                return self.empty_response
            
            # Read chat history in LLM fromat
            chat_history = await self.chat_history_service.read_chat_history(message['chat']['id'])
            if user_text != '':
                if await self.chat_history_service.is_message_deprecated(2, message, reply_to_message_id):
                    return self.empty_response
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
                    temperature=self.config_manager.get("temperature"),
                    logger=self.logger
                    )
                await chat_agent.initialize_agent()
                answer = chat_agent.agent.run(
                    input=message_text, 
                    chat_history=chat_history
                )
                # Return empty if deprecated
                if await self.chat_history_service.is_message_deprecated(3, message, reply_to_message_id):
                    return self.empty_response
                
                # Save to chat history
                await self.chat_history_service.save_to_chat_history(
                    message['chat']['id'],
                    answer,
                    message['message_id'],
                    'AIMessage',
                    message['from']['first_name'],
                    'llm'
                )

                self.logger.info('Replying in '+str(message['chat']['id']))
                self.logger.info(f'Answer: {answer}')
                return self.text_response(answer)

application = Application()
app = application.app
