from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
import os


def partners_bot_confirmphone(phoneNumber, chatId):
	login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
	password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

	session = Session()
	session.auth = HTTPBasicAuth(login, password)

	clientPath = [
		'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
		'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
		'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
		]
	# clientPath = ['http://10.2.4.141/Test_Piter_MRM/ws/Telegram.1cws?wsdl']
	results = []
	# Get only the right 10 symbols of the phone number
	phoneNumber = phoneNumber[-10:]
	for w in clientPath:
		client = Client(w, transport=Transport(session=session))
		res = client.service.partnersPhoneConfirmation(phoneNumber, chatId)
		results.append(res)
	return results


def mrmsupport_bot_confirmphone(phoneNumber,chatId, clientPath):
	login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
	password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

	session = Session()
	session.auth = HTTPBasicAuth(login, password)

	
	for w in clientPath:
		client = Client(w, transport=Transport(session=session))
		res = client.service.phoneConfirmation(phoneNumber, chatId)
		if res and res['result']:
			return res
	return  res


def mrmsupport_bot_writelink(phoneNumber,link, clientPath):
	login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
	password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

	session = Session()
	session.auth = HTTPBasicAuth(login, password)

	"""clientPath = [
		'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
		'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
		'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
		]"""
	for w in clientPath:
		client = Client(w, transport=Transport(session=session))
		res = client.service.writeLink(phoneNumber, link)
		if res :
			return res
	return  res


def mrmsupport_bot_user_info(user_id, clientPath):
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    """clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
        ]"""
    results = []
    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        res = client.service.user_info(user_id)
        if res and res['result']:
            results.append(str(res))
    return results
