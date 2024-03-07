import os
import requests
import logging
from typing import Any, Dict

class OneCProxyService:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.logger = logging.getLogger(self.__class__.__name__)
        self.token = os.environ.get('MRMSUPPORTBOT_TOKEN', '')

    def _make_request(self, endpoint: str, method: str, headers: Dict[str, str], data: Any):
        url = f"{self.base_url}/{endpoint}"
        try:
            self.logger.info(f"Request to {endpoint} Endpoint: {url}")
            if method.lower() == 'post':
                response = requests.post(url, headers=headers, json=data)
            # You can add support for other HTTP methods here (GET, PUT, DELETE)
            # elif method.lower() == 'get':
            #     response = requests.get(url, headers=headers, params=data)
            # Additional methods can be implemented as necessary
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            self.logger.info(f"{endpoint} Endpoint Response: {response}")
            response.raise_for_status()  # Raise an exception for HTTP error codes
            return response.json()       # Return JSON response

        except requests.RequestException as e:
            self.logger.error(f"Request to {endpoint} failed: {e}")
            return []

    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        headers = {'Content-Type': 'application/json'}
        data = {'token': self.token, 'user_id': user_id}
        return self._make_request(endpoint="user_info", method="POST", headers=headers, data=data)
    
    async def get_actual_version(self) -> Dict[str, Any]:
        headers = {'Content-Type': 'application/json'}
        return self._make_request(endpoint="actual_version", method="POST", headers=headers, data={})
