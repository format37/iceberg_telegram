# from langchain_community.tools import StructuredTool
from langchain.tools.base import StructuredTool
from langchain_experimental.utilities import PythonREPL
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from pydantic import BaseModel, Field
from langchain.tools import Tool
# from langchain.agents import initialize_agent
import os
from langchain.chains import RetrievalQA
import requests
import uuid
from langchain.agents import initialize_agent, AgentType
import json
import pandas as pd
import datetime
import time

class DocumentProcessor:
    def __init__(self, context_path):
        self.context_path = context_path

    def process_documents(self, logger):
        context_path = self.context_path
        logger.info(f"Processing documents from {context_path}")
        loader = DirectoryLoader(context_path, glob="*", loader_cls=TextLoader)
        docs = loader.load()
        logger.info(f"Loaded {len(docs)} documents")
        api_key = os.environ.get('OPENAI_API_KEY', '')
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        text_splitter = RecursiveCharacterTextSplitter()
        documents = text_splitter.split_documents(docs)
        logger.info(f"Split {len(documents)} documents")
        vector = DocArrayInMemorySearch.from_documents(documents, embeddings)
        return vector.as_retriever()
    

class TextOutput(BaseModel):
    text: str = Field(description="Text output")

class BotActionType(BaseModel):
    val: str = Field(description="Tool parameter value")

class DocumentInput(BaseModel):
    question: str = Field()

class mrm_master_log_args(BaseModel):
    # param: str = Field(description="""Предоставьте имя мастера""")
    master_name: str = Field(description="master_name")
    reply_to_message_id: int = Field(description="reply_to_message_id")

class ChatAgent:
    def __init__(self, retriever, model, temperature, logger, bot_instance, chat_id):
        # Initialize logging
        # logging.basicConfig(level=logging.INFO)
        self.logger = logger
        self.logger.info(f'ChatAgent init with model: {model} and temperature: {temperature}')
        # self.config = bot_instance.config
        self.config = {
            'model': model,
            'temperature': temperature
        }
        self.retriever = retriever
        self.agent = None
        self.bot_instance = bot_instance
        self.chat_id = chat_id

    def initialize_agent(self):
        llm = ChatOpenAI(
            openai_api_key=os.environ.get('OPENAI_API_KEY', ''),
            model=self.config['model'],
            temperature=self.config['temperature'],
        )
        tools = []
        # Tool: Retrieval
        retrieval_tool = Tool(
                args_schema=DocumentInput,
                name='Issue retrieval database',
                description="Issue retrieval database содержит набор решений различных ситуаций которые имели место в прошлом. Испольуйте как можно чаще что бы найти решение проблемы.",
                func=RetrievalQA.from_chain_type(llm=llm, retriever=self.retriever),
            )
        tools.append(retrieval_tool)
        # Tool: mrm_master_log
        mrm_logs_tool = StructuredTool.from_function(
                func=self.mrm_master_log,
                name="Логи мастера",
                description="Получает последние сообщения из логов по имени мастера. Вам следует предоставить Имя мастера и reply_to_message_id в качестве параметров.",
                args_schema=mrm_master_log_args,
                return_direct=False,
                # coroutine= ... <- you can specify an async method if desired as well
            )
        tools.append(mrm_logs_tool)
        # Tool python interpreter
        python_repl = PythonREPL()
        repl_tool = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=python_repl.run,
            return_direct=False,
        )
        tools.append(repl_tool)
        # agent_chain = initialize_agent(tools, llm, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION)
        self.agent = initialize_agent(
            tools,
            llm,
            # agent='chat-conversational-react-description',
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )

    def mrm_master_log(self, master_name, reply_to_message_id):

        self.logger.info(f"mrm_master_log master_name: {master_name} reply_to_message_id: {reply_to_message_id}")
        url = "https://service.icecorp.ru:7403/request_1c"  # Replace with your server URL
        # Date format sample 2024-02-01T13:00:00
        current_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        query_params = {
            "Идентификатор": "mrm_log_0",
            "master_name": master_name,
            "current_date": current_date
        }

        response = requests.post(url, json=query_params)

        if response.status_code == 200:
            result_str = response.json()["result"]
            first_lines = {}
            for key in result_str:
                if result_str[key]:
                    first_lines[key] = [result_str[key][0]]

            # Create an empty list to store the HTML tables
            html_tables = []

            # Iterate over each region
            for region, data in result_str.items():
                # Convert the data for the current region to a DataFrame
                df = pd.DataFrame(data)

                # Convert the DataFrame to an HTML table
                html_table = df.to_html(index=False)

                # Add the region name as a heading and append the HTML table to the list
                html_tables.append(f"<h2>{region}</h2>{html_table}")

            # Join the HTML tables with a newline separator
            combined_html = "\n".join(html_tables)

            # Save the combined HTML tables as a temporary file with a unique name
            uid_name = str(uuid.uuid4())
            if not os.path.exists("/tmp"):
                os.makedirs("/tmp")
            filename = f"/tmp/{uid_name}.html"
            with open(filename, "w") as f:
                f.write(combined_html)
                self.logger.info(f"HTML tables saved to {filename}")

            # Send the HTML file to the user via bot
            with open(filename, 'rb') as f:
                self.logger.info(f"Sending {filename} to the chat_id: {reply_to_message_id}")
                self.bot_instance.send_document(
                    self.chat_id,
                    f,
                    reply_to_message_id=reply_to_message_id
                )

            answer_str = f"Файл логов в полном составе отправлен в чат. Последняя строка логов: {json.dumps(first_lines)}"
        else:
            answer_str = f"Error: {response.status_code}"
        self.logger.info(f"mrm_master_log answer_str: {answer_str}")
        return answer_str        

    @staticmethod
    async def create_structured_tool(func, name, description, return_direct):
        print(f"create_structured_tool name: {name} func: {func}")
        return StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            args_schema=BotActionType,
            return_direct=return_direct,
        )
