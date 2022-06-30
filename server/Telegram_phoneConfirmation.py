from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
import os


def mrmsupport_bot_confirmphone(phoneNumber,chatId):
	login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
	password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

	session = Session()
	session.auth = HTTPBasicAuth(login, password)

	clientPath = ['http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl', 'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl', 'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl']
	for w in clientPath:
		client = Client(w, transport=Transport(session=session))
		res = client.service.phoneConfirmation(phoneNumber, chatId)
		if res and res['result']:
			return res
	return  res


def mrmsupport_bot_writelink(phoneNumber,link):
	login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
	password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

	session = Session()
	session.auth = HTTPBasicAuth(login, password)

	clientPath = ['http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl', 'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl', 'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl']
	for w in clientPath:
		client = Client(w, transport=Transport(session=session))
		res = client.service.writeLink(phoneNumber, link)
		if res :
			return res
	return  res
