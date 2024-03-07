from langchain_community.tools import StructuredTool
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from pydantic import BaseModel, Field
from langchain.tools import Tool
from langchain.agents import initialize_agent
import os
from langchain.chains import RetrievalQA


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

class ChatAgent:
    def __init__(self, retriever, model, temperature, logger):
        # Initialize logging
        # logging.basicConfig(level=logging.INFO)
        self.logger = logger
        self.logger.info(f'ChatAgent init with model: {model} and temperature: {temperature}')
        # self.config = bot_instance.config
        self.config = {
            'model': model, # 'gpt-4-1106-preview' or 'gpt-3.5-turbo'
            'temperature': temperature
        }
        self.retriever = retriever
        self.agent = None        

    async def initialize_agent(self):
        llm = ChatOpenAI(
            openai_api_key=os.environ.get('OPENAI_API_KEY', ''),
            model=self.config['model'],
            temperature=self.config['temperature'],
        )
        tools = []
        tools.append(
            Tool(
                args_schema=DocumentInput,
                name='Retrieval search database',
                description="Questions, answers, instructions",
                func=RetrievalQA.from_chain_type(llm=llm, retriever=self.retriever),
            )
        )
        self.agent = initialize_agent(
            tools,
            llm,
            agent='chat-conversational-react-description',
            verbose=True,
            handle_parsing_errors=True
        )

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
