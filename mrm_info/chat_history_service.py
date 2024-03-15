import json
import os
from pathlib import Path
import time as py_time
import aiofiles
from langchain.schema import AIMessage, HumanMessage

class ChatHistoryService:
    def __init__(self, data_dir, logger):
        self.data_dir = data_dir
        self.logger = logger

    def chat_log_path(self, chat_id):
        return os.path.join(self.data_dir, str(chat_id))

    async def save_to_chat_history(
            self, 
            chat_id, 
            message_text, 
            message_id, 
            message_type, 
            user_name, 
            event_id='default'
            ):
        self.logger.info(f'[{event_id}] Saving message to chat history for chat_id: {chat_id} for message_id: {message_id}')
        message_date = py_time.strftime('%Y-%m-%d-%H-%M-%S', py_time.localtime())
        parsed_time = py_time.strptime(message_date, '%Y-%m-%d-%H-%M-%S')
        unix_timestamp = int(py_time.mktime(parsed_time))
        # log_file_name = f'{message_date}_{message_id}_{event_id}.json'
        log_file_name = f'{unix_timestamp}_{message_id}_{event_id}.json'

        chat_log_dir = self.chat_log_path(chat_id)
        Path(chat_log_dir).mkdir(parents=True, exist_ok=True)
        
        full_path = os.path.join(chat_log_dir, log_file_name)
        async with aiofiles.open(full_path, 'w') as log_file:
            await log_file.write(json.dumps({
                "type": message_type,
                "text": message_text,
                "date": message_date,
                "message_id": message_id,
                "name_of_user": user_name
            }, ensure_ascii=False))
    
    async def configuration_in_history(self, chat_id):
        chat_log_path = os.path.join(self.data_dir, str(chat_id))
        # Create the chat log path if not exist
        Path(chat_log_path).mkdir(parents=True, exist_ok=True)
        # self.crop_queue(chat_id=chat_id)
        self.logger.info(f'DEBUG: Listing chat_log_path: {chat_log_path}')
        for log_file in sorted(os.listdir(chat_log_path)):
            self.logger.info(f'DEBUG: log_file: {log_file}')
            # Return True if 'configuration' word is in the file_name
            if 'configuration' in log_file:
                self.logger.info(f'DEBUG: configuration_in_history chat_id: {chat_id} True')
                return True
        self.logger.info(f'DEBUG: NOT configuration_in_history chat_id: {chat_id} False')
        return False
    
    async def date_of_latest_message(self, chat_id: str):
        self.logger.info(f'DEBUG: date_of_latest_message chat_id: {chat_id}')
        chat_log_path = self.chat_log_path(chat_id)
        Path(chat_log_path).mkdir(parents=True, exist_ok=True)
        log_files = os.listdir(chat_log_path)

        if not log_files:
            self.logger.info(f'No chat history found for chat_id: {chat_id}')
            return 0

        self.logger.info(f'Chat history for chat_id: {chat_id} is {len(log_files)} messages.')

        latest_date = '0'
        for log_file in sorted(log_files, reverse=True):
            try:
                # Extract date from file_name = f'{message_date}_{message_id}.json'
                message_date = int(log_file.split('_')[0])
                latest_date = max(latest_date, message_date)
            except Exception as e:
                self.logger.info(f'Error reading chat history file {log_file}: {e}')
                os.remove(os.path.join(chat_log_path, log_file))
        
        return latest_date

    async def is_message_deprecated(self, event_id, message, reply_to_message_id):
        current_date = message['date']
        latest_date = await self.date_of_latest_message(str(reply_to_message_id))
        self.logger.info(f'[{event_id}] current_date: {current_date} latest_date: {latest_date}')
        
        if current_date < latest_date:
            self.logger.info(f'[{event_id}] Cancelling task: Message is not the latest')
            return True
        return False

    async def read_chat_history(self, chat_id: str):
        """Reads the chat history from a folder and returns it as a list of messages."""
        chat_history = []
        chat_log_path = self.chat_log_path(chat_id)
        Path(chat_log_path).mkdir(parents=True, exist_ok=True)
        self.logger.info(f'Reading chat history from: {chat_log_path}')
        
        for log_file in sorted(os.listdir(chat_log_path)):
            full_path = os.path.join(chat_log_path, log_file)
            try:
                with open(full_path, 'r') as file:
                    message = json.load(file)
                    if message['type'] == 'AIMessage':
                        chat_history.append(AIMessage(content=message['text']))
                    elif message['type'] == 'HumanMessage':
                        chat_history.append(HumanMessage(content=message['text']))
            except Exception as e:
                self.logger.error(f'Error reading chat history file {log_file}: {e}')
                # Remove problematic file
                os.remove(full_path)

        return chat_history