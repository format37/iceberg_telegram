import requests
import json
# import sys

# Server base URL
base_url = "http://service.icecorp.ru:7403"  # Adjust as necessary

# Testing the /test endpoint
def test_endpoint():
    url = f"{base_url}/test"
    response = requests.get(url)
    if response.status_code == 200:
        print("Test Endpoint Response:", response.json())
    else:
        print("Failed to get response from test endpoint")

# Testing the /user_info endpoint
def user_info_endpoint(token, user_id):
    url = f"{base_url}/user_info"
    headers = {'Content-Type': 'application/json'}
    data = {
        'token': token,
        'user_id': user_id
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("User Info Endpoint Response:", response.json())
    else:
        print(f"Failed to get response from user info endpoint. Status Code: {response.status_code}")

if __name__ == "__main__":
    # Call test endpoint
    test_endpoint()
    
    # Example token and user_id for user_info endpoint
    # Take token from parameter client.py token
    """if len(sys.argv) < 2:
        print("Usage: python client.py <token>")
        sys.exit(1)
    example_token = sys.argv[1]"""
    # Read from file
    with open('token.txt', 'r') as file:
        example_token = file.read().replace('\n', '')
    example_user_id = "117036340"
    
    # Call user_info endpoint with the example token and user_id
    user_info_endpoint(example_token, example_user_id)
