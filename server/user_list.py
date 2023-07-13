from telethon import TelegramClient
from datetime import datetime as dt
import pandas as pd
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
import asyncio


def mrmsupport_bot_user_info(user_id):
    login = 'mrm'
    password = 'mrmmrm'

    session = Session()
    session.auth = HTTPBasicAuth(login, password)

    # Settings. 1C web services ++
    clientPath = [
        'http://10.2.4.123/productionMSK/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionNNOV/ws/Telegram.1cws?wsdl',
        'http://10.2.4.123/productionSPB/ws/Telegram.1cws?wsdl'
        ]
    # Settings. 1C web services --

    results = []
    for w in clientPath:
        client = Client(w, transport=Transport(session=session))
        res = client.service.user_info(user_id)
        if res and res['result']:
            results.append(res)
    return results


async def main():

    # Settings. Chats & affilates ++
    chats = {
        'Офис мастера. Москва': -1001273219988,
        'Офис мастера. Питер': -1001285914663,
        'Офис мастера. Нижний Новгород': -1001410518922,
        'Офис мастера. Воронеж': -1001597625789,
        'Офис мастера. Ростов-на-Дону': -1001460744446,
        'Офис мастера. Краснодар': -1001667504749
    }
    affilates = {
        'МСК': 'Офис мастера. Москва',
        'СПБ': 'Офис мастера. Питер',
        'ННОВ': 'Офис мастера. Нижний Новгород',
        'ВРН': 'Офис мастера. Воронеж',
        'РнД': 'Офис мастера. Ростов-на-Дону',
        'КРД': 'Офис мастера. Краснодар'
    }
    # Settings. Chats & affilates --

    print('\n===', dt.now(), '\nListed the following chats:\n')
    for chat in chats:
        print(chat)

    message = '\n===\nTo authenticate, please go to\n'
    message += 'https://my.telegram.org/apps\n'
    message += 'and get required values:\n'
    print(message)
    api_id = int(input('Api id: '))
    api_hash = input('Api hash: ')
    app_name = input('App name: ')

    client = TelegramClient(app_name, api_id, api_hash)
    print('\nConnecting...')
    await client.connect()
    if not await client.is_user_authorized():
        phone_number = input('Phone number: ')
        await client.send_code_request(phone_number)
        await client.sign_in(phone = phone_number)
        await client.sign_in(code = input('Enter code: '))
        print('Connected!\n')
    await client.start()
    print(dt.now(), "Client started")

    print("Getting the telegram chats participants")
    users = []
    for chat in chats:
        print('"'+chat+'"')
        async for user in client.iter_participants(chats[chat]):
            users.append({
                'chat': chat,
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone
            })
    print(dt.now(), "Collected ", len(users), " participants:")

    df = pd.DataFrame(columns=['chat','id','first_name','last_name','username','phone'])
    for user in users:
        df = df.append({
            'chat': user['chat'],
            'id': user['id'],
            'username': user['username'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'phone': user['phone']
        }, ignore_index=True)

    for chat in chats:
        print(chat, len(df[df.chat==chat]))
    
    df.to_csv('telegram_users.csv', index=False)
    print(dt.now(), "Saved to telegram_users.csv")

    print(dt.now(), "Getting the additional information about users from 1C")
    df['result'] = [False for i in range(len(df))]
    df['affilate'] = ['' for i in range(len(df))]
    df['name'] = ['' for i in range(len(df))]
    df['remove_date'] = ['' for i in range(len(df))]
    df['fire_date'] = ['' for i in range(len(df))]
    for idx, row in df.iterrows():
        results = mrmsupport_bot_user_info(row.id)
        print(
            dt.now(), 
            idx, '/', len(df), 
            'found results:', len(results), 
            'chat:', row.chat,
            'user id:', row.id
            )
        for result in results:
            df.loc[(df.id==row.id) & (df.chat==affilates[result.affilate]), 'result'] = result.result
            df.loc[(df.id==row.id) & (df.chat==affilates[result.affilate]), 'affilate'] = result.affilate
            df.loc[(df.id==row.id) & (df.chat==affilates[result.affilate]), 'name'] = result.name
            df.loc[(df.id==row.id) & (df.chat==affilates[result.affilate]), 'remove_date'] = result.remove_date
            df.loc[(df.id==row.id) & (df.chat==affilates[result.affilate]), 'fire_date'] = result.fire_date

    df.to_csv('telegram_1c_users.csv')
    print(dt.now(), "Saved to telegram_1c_users.csv")

    nonexists = df[
        (df.result==False) |
        (df.remove_date!='01.01.0001 0:00:00') |
        (df.fire_date!='01.01.0001 0:00:00')
    ]
    print("Users, who shouldn't be in chats:", len(nonexists))
    nonexists.to_csv('telegram_nonexists.csv', index=False)
    print(dt.now(), "Saved to telegram_nonexists.csv")
    print("Done")


if __name__ == '__main__':
    asyncio.run(main())
