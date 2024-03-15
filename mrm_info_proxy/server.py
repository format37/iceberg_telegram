from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import logging
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
from onec_request import OneC_Request

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})

@app.post("/actual_version")
async def call_actual_version(request: Request):
    logger.info(f'call_actual_version. request: {request}')
    server_address = 'https://service.icecorp.ru/apk/'
    version = 807
    try:
        apt_list_path = '/mnt/soft/apk'
        # Find the name of the latest apk, using sorting by name descending
        for file in sorted(os.listdir(apt_list_path), reverse=True):
            if file.endswith(".apk"):
                logger.info("mrmsupport_bot_test. latest apk: "+str(file))
                apk_link = f'{server_address}{file}'
                version = file.split('.')[0]
                break
        
    except Exception as e:
        logger.error("mrmsupport_bot_test. apk_link: "+str(e))
    apk_link = f'{server_address}{version}.apk' # Default link
    return JSONResponse(content={
        "version": version,
        "link": apk_link
        })

@app.post("/request_1c")
async def call_request_1c(request: Request):
    logger.info(f'call_request_1c. request: {request}')
    try:
        query_params = await request.json()
        logger.info(f"request_1c query_params: {query_params}")
        onec_request = OneC_Request('1c.json')
        result_dfs = onec_request.execute_query(query_params)
        
        # Convert each DataFrame to a string and concatenate them
        result_str = '\n'.join(df for df in result_dfs)
        
        logger.info(f"Received from mrm_logs:\n{result_str}")
        return JSONResponse(content={"result": result_str})
    except Exception as e:
        logger.error(f"Error in call_request_1c: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/user_info")
async def call_user_info(request: Request):
    logger.info(f'call_user_info. request: {request}')
    results = []
    try:
        data = await request.json()
        token = data.get('token', '')
        if token != os.environ.get('MRMSUPPORTBOT_TOKEN', ''):
            # raise HTTPException(status_code=401, detail="Invalid token")
            logger.info(f'Invalid token: {token}')
            return results
    except Exception as e:
        # logger.error('call_user_info error: ' + str(e))
        # raise HTTPException(status_code=400, detail="Invalid request")
        logger.info(f'Invalid request: {data}')
        return results

    
    # user_id is Telegram message['forward_from']['id']
    user_id = data.get('user_id', '')
    
    logger.info(f'call_user_info. user_id: {user_id}')
    clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
    ]
    login = os.environ.get('MRMSUPPORTBOT_AUTH_LOGIN', '')
    password = os.environ.get('MRMSUPPORTBOT_AUTH_PASSWORD', '')

    session = Session()
    session.auth = HTTPBasicAuth(login, password)
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
