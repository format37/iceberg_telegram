import base64
import os
import requests
from pathlib import Path

class PhotoDescriptionService:
    def __init__(self, temp_dir, api_key, llm_model='gpt-4-vision-preview', logger=None):
        self.temp_dir = temp_dir
        self.api_key = api_key
        self.llm_model = llm_model
        self.logger = logger

    @staticmethod
    async def encode_image_to_base64(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def download_photo(self, bot, file_id):
        Path(self.temp_dir).mkdir(exist_ok=True)
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = os.path.join(self.temp_dir, f'{file_id}.jpg')
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        return file_path

    async def remove_temp_file(self, file_path):
        os.remove(file_path)

    async def request_photo_description(self, image_base64):
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        prompt_text = "Пожалуйста, опишите максимально детально, что вы видите на этом изображении?"

        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            "max_tokens": 1500
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            response_json = response.json()
            description = response_json['choices'][0]['message']['content']
            return description
        response.raise_for_status()

    async def get_photo_description(self, bot, message):
        user_text = ''
        photo_id = message['photo'][-1]['file_id']
        file_path = await self.download_photo(bot, photo_id)

        try:
            base64_image = await self.encode_image_to_base64(file_path)
            description = await self.request_photo_description(base64_image)
            user_text += '\nОписание скриншота, который прислал пользователь:\n' + description

            if 'caption' in message:
                user_text += '\nUser comment: ' + message['caption']
        finally:
            await self.remove_temp_file(file_path)

        return user_text