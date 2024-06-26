# -*- coding: utf-8 -*-
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
import os
import ast
import datetime

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

        self.chat_agent = None
        """self.chat_agent = ChatAgent(
            retriever=self.retriever, 
            model=self.config_manager.get("model"), 
            temperature=self.config_manager.get("temperature"),
            logger=self.logger
            )
        self.chat_agent.initialize_agent()"""

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

            granted_chats = [
                '-1001853379941', # MRM master info МРМ мастер, 
                '-1002094333974', # botchat (test)
                '-1002087087929' # TehPodMRM Comments
            ]
            
            answer = ""
            if not str(message['chat']['id']) in granted_chats:
                return self.empty_response

            if 'forward_from' in message or \
                'forward_origin' in message or \
                ('reply_to_message' in message and message['reply_to_message']['from']['is_bot']):
                pass # Ok, we need to send a tech report
            else:
                # Save to hostory
                await self.chat_history_service.save_to_chat_history(
                    message['message_id'],
                    message['text'],
                    message['message_id'],
                    'HumanMessage',
                    message['from']['first_name'],
                    '0_incoming'
                )
                # Return empty
                self.logger.info('0: Not a reply to bot')
                return self.empty_response

            token = None
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
            
            if token:
                pass
            else:
                answer = """Не удалось определить токен бота.
Пожалуйста обратитесь к администратору."""
                return self.text_response(answer)
            
            if 'message_thread_id' in message:
                reply_to_message_id = message['message_thread_id']
            elif 'reply_to_message' in message and \
                'message_id' in message['reply_to_message']:
                reply_to_message_id = message['reply_to_message']['message_id']
            else:
                reply_to_message_id = message['message_id']

            if 'message_thread_id' in message:
                message_thread_id = message['message_thread_id']
            else:
                message_thread_id = message['message_id']

            message_text = ''
            server_api_uri = 'http://localhost:8081/bot{0}/{1}'
            telebot.apihelper.API_URL = server_api_uri
            self.logger.info(f'Setting API_URL: {server_api_uri}')

            server_file_url = 'http://localhost:8081'
            telebot.apihelper.FILE_URL = server_file_url
            self.logger.info(f'Setting FILE_URL: {server_file_url}')
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
            await self.chat_history_service.save_to_chat_history(                
                message_thread_id,
                message_text,
                message_thread_id,
                'HumanMessage',
                message['from']['first_name'],
                '0_incoming',
                date_override=message['date']
            )

            if 'reply_to_message' in message and \
                'from' in message['reply_to_message'] and \
                'username' in message['reply_to_message']['from']:
                if 'mrminfotestbot' in message['reply_to_message']['from']['username'] or \
                    'mrminfobot' in message['reply_to_message']['from']['username']:
                    pass # Ok, we need to reply to direct message to bot
                else:
                    # Return empty
                    self.logger.info('0: Not a reply to bot')
                    return self.empty_response
            
            reply = '[\n'
            results = []
            
            if not await self.chat_history_service.configuration_in_history(reply_to_message_id):
                actual_version_info = await self.onec_service.get_actual_version()
                if 'forward_origin' in message and 'forward_from' in message:
                    phone_number = message['forward_from']['phone_number'] if 'phone_number' in message['forward_from'] else ''
                    user_name = message['forward_from']['first_name'] if 'first_name' in message['forward_from'] else ''
                    results = await self.onec_service.get_user_info(message['forward_from']['id'], phone_number, user_name)
                    for info_id in range(len(results)):
                        self.logger.info(f'# DEBUG results: {results}')
                        # Convert item to JSON using ast
                        results[info_id] = ast.literal_eval(results[info_id])                        
                        app_version = results[info_id]['app_version']
                        if app_version == actual_version_info['version']:
                            results[info_id]['is_update_required'] = f'Версия актуальна. Обновление не требуется.'
                        else:
                            results[info_id]['is_update_required'] = f'Необходимо обновление приложения до версии {actual_version_info["version"]}!'
                        # Add current date to the results. Get date from the system time
                        results[info_id]['current_date'] = f'{datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")}'
                        # Replace 'name' with 'master_name' in the results
                        results[info_id]['master_name'] = results[info_id].pop('name')
                        # Replace " with ' in the results
                        for key, value in results[info_id].items():
                            if isinstance(value, str):
                                results[info_id][key] = value.replace('"', "'")
                                self.logger.info(f'# DEBUG results[{info_id}][{key}]: {results[info_id][key]}')

                            
                else:
                    results.append('Техническая информация о пользователе недоступна')
                # Add information about the latest version of the application
                if len(actual_version_info) > 0:
                    new_element = {
                        'Available Update Version': actual_version_info['version'],
                        'Update link': actual_version_info['link']
                    }
                    results.append(new_element)

                # Before joining the results, convert each item to a string if it's not already one
                # results_as_strings = [json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else str(item) for item in results]
                results_as_strings = []
                for item in results:
                    if isinstance(item, dict):
                        # results_as_strings.append(json.dumps(item, ensure_ascii=False))
                        current_result = '{'
                        for key, value in item.items():
                            current_result += f'"{key}": "{value}",\n'
                        # Remove the last comma
                        current_result = current_result[:-2]
                        # Add the new line and close the dictionary
                        current_result += '\n}'
                        results_as_strings.append(current_result)

                    else:
                        results_as_strings.append(str(item))
                # Now you can safely join the string representations of your results
                reply += ',\n'.join(results_as_strings)
                answer = reply + '\n]'

                # Save to chat history
                await self.chat_history_service.save_to_chat_history(
                    message_thread_id,
                    answer,
                    message_thread_id,
                    'AIMessage',
                    message['from']['first_name'],
                    '1_configuration',
                    date_override=message['date']
                )

            if answer != '':
                bot.send_message(
                    message['chat']['id'], 
                    answer, 
                    reply_to_message_id=message_thread_id
                    )
            
            user_text = message_text
            self.logger.info(f'[4] DEBUG: User text: {user_text}')

            if await self.chat_history_service.is_message_deprecated(1, message, reply_to_message_id):
                return self.empty_response
            
            # Avoid of answering if message is not reply to bot
            if 'reply_to_message' in message and \
                'from' in message['reply_to_message'] and \
                'username' in message['reply_to_message']['from']:
                if 'mrminfotestbot' in message['reply_to_message']['from']['username'] or \
                    'mrminfobot' in message['reply_to_message']['from']['username']:
                    pass # Ok, we need to reply to direct message to bot
                else:
                    # Return empty
                    self.logger.info('1: Not a reply to bot')
                    return self.empty_response
            else:
                # Return empty
                self.logger.info('2: Not a reply to bot')
                return self.empty_response
            
            # Read chat history in LLM fromat
            # chat_history = await self.chat_history_service.read_chat_history(message['chat']['id'])
            chat_history = await self.chat_history_service.read_chat_history(message_thread_id)
            # chat_history = await self.chat_history_service.read_chat_history(
            if user_text != '':
                if await self.chat_history_service.is_message_deprecated(2, message, reply_to_message_id):
                    return self.empty_response
                user_info = str(results) if len(results) > 0 else "Not provided" # Tech info from 1C
                master_name = await self.chat_history_service.get_master_name_from_configuration(message_thread_id)
                if len(chat_history) < 3:
                    message_text = f"""Вы сотрудник технической поддержки Мобильного приложения мастера. Вы находитесь в группе технической поддержки с другими сотрудниками.
На данный момент обсуждается запрос от пользователя: "{user_text}"
Техническая информация о пользвателе:
{user_info}
reply_to_message_id: {reply_to_message_id}
master_name: {master_name}
Не предлагайте ничего если вас об этом не спросят.
Вам доступен набор инструментов, которые вы можете использовать по своему усмотрению.
Не предлагайте коллегам использовать ваши инструменты, они доступны только вам.
Ваш ответ должен быть на русском языке.
В начале ответа перечислите инструменты которые были использованы.
"""
                else:
                    message_text = f"""Вы сотрудник технической поддержки Мобильного приложения мастера.
reply_to_message_id: {reply_to_message_id}
master_name: {master_name}
Используйте доступные вам инструменты, если необходимо. На данный момент к вам обращаются с сообщением: {user_text}
"""
                # message_text = message_text.replace('\n', ' ')
                    
                if self.chat_agent is None:
                    self.chat_agent = ChatAgent(
                        retriever=self.retriever,
                        model=self.config_manager.get("model"),
                        temperature=self.config_manager.get("temperature"),
                        logger=self.logger,
                        bot_instance=bot, # Working only with a single bot
                        chat_id=message['chat']['id']
                        )
                    self.chat_agent.initialize_agent()

                # Log the count of messages in chat history
                self.logger.info(f'Calling LLM with chat history length: {len(chat_history)}')
                answer = self.chat_agent.agent.run(
                    input=message_text, 
                    chat_history=chat_history,
                    reply_to_message_id=reply_to_message_id
                )
                # Return empty if deprecated
                if await self.chat_history_service.is_message_deprecated(3, message, reply_to_message_id):
                    return self.empty_response
                
                # Save to chat history
                """await self.chat_history_service.save_to_chat_history(
                    message['chat']['id'],
                    answer,
                    message_thread_id,
                    'AIMessage',
                    message['from']['first_name'],
                    '1_llm'
                )"""
                await self.chat_history_service.save_to_chat_history(
                    message_thread_id,
                    answer,
                    message_thread_id,
                    'AIMessage',
                    message['from']['first_name'],
                    '1_llm'
                )

                self.logger.info('Replying in '+str(message['chat']['id']))
                self.logger.info(f'Answer: {answer}')
                return self.text_response(answer)

application = Application()
app = application.app
