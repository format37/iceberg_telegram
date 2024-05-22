import logging
import json
import time
import pandas as pd
from requests.auth import HTTPBasicAuth
from requests import Session
from zeep import Client
from zeep.transports import Transport
import io

class OneC_Request:
    def __init__(self, config):
        # self.config = json.load(open(config_file))
        self.config = config
        self.login = self.config['login']
        self.password = self.config['password']
        self.clients = self.config['clientPath']
        self.session = Session()
        self.session.auth = HTTPBasicAuth(self.login, self.password)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def execute_query(self, query_params, df_dtype=None):
        self.logger.info(f'Executing 1C query with params: {query_params}')
        result_dfs = {}

        for client_name, client_url in self.clients.items():
            start_time = time.time()
            client = Client(client_url, transport=Transport(session=self.session))
            self.logger.info(f'\n\nCalling ws for: {client_name}')

            response = client.service.ExecuteQuery(str(query_params))
            end_time = time.time()
            self.logger.info(f'Execution time: {end_time - start_time}')

            if 'Ошибка' in str(response):
                self.logger.error(f'Error: {response}')
            else:
                data = json.loads(response)
                self.logger.info(f'Status OK: {data["Состояние"]}')
                if data["СтрОшибки"] != '':
                    self.logger.info(f'Error message: {data["СтрОшибки"]}')
                self.logger.info(f'Server-side duration: {data["Длительность"]/1000}')

                csv_table = data['ТаблицаЗначений']
                if df_dtype:
                    df = pd.read_csv(io.StringIO(csv_table), sep=';', dtype=df_dtype)
                else:
                    df = pd.read_csv(io.StringIO(csv_table), sep=';')
                result_dfs[client_name] = df

        self.logger.info('Done')
        return result_dfs

    def execute_query_from_file(self, request_file, df_dtype=None):
        with open(request_file) as file:
            query_params = json.load(file)
        return self.execute_query(query_params, df_dtype)
