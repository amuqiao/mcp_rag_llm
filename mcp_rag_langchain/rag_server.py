# -*- encoding: utf-8 -*-

"""
1.索引的构建
2.server服务的封装，mcp的封装
"""





import asyncio
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
# from langchain_community.chains import RetrievalQA
from langchain_classic.chains import RetrievalQA
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

class RAGSystem(object):
    def __init__(self, config):
        self.config = config
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "qwen-plus"),
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY")
        )
        # 优先从环境变量获取本地模型路径，否则使用默认本地路径
        embed_model_path = os.getenv("EMBED_MODEL_PATH", "e:/github_project/models/bge-large-zh-v1.5")
        self.embedding = HuggingFaceEmbeddings(
            model_name=embed_model_path,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectorstore=Chroma(
            collection_name=self.config["collection_name"],
            embedding_function=self.embedding,
            persist_directory=self.config["persist_dir"]
        )

        self.retriver = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k":self.config.get("top_k", 5)
            }
        )
    def _load_documents(self, file_paths):
        docs=[]
        for path in file_paths:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.endswith(".txt"):
                loader = TextLoader(path, encoding="utf-8")
            else:
                raise ValueError(f"跳过不支持的文件格式: {path}")
            docs.extend(loader.load())
        return docs

    def _chunk_documents(self, docs):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.get("chunk_size", 500),
            chunk_overlap=self.config.get("chunk_overlap", 50),
            length_function=len,
            is_separator_regex=True
        )
        return text_splitter.split_documents(docs)

    def build_knowledge(self, file_paths):
        #1.加载文档
        raw_docs = self._load_documents(file_paths)

        #2.切分文档-切块
        chunks = self._chunk_documents(docs = raw_docs)

        #3.生成向量并存储
        self.vectorstore.add_documents(chunks)
        self.vectorstore.persist()
        print(f"知识库构建完成,文档块数为:{len(chunks)}")

    def query(self, question):
        qa_chain=RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriver,
            return_source_documents=True
        )
        result = qa_chain.invoke({"query": question})
        return_result = {
            "answer": result["result"],
            "sources":[
                {
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", "N/A")
                }
                for doc in result["source_documents"]
            ]
        }
        return return_result
config = {
    "persist_dir": "./data/rag_db",
    "collection_name": "rag",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 5
}

rag=RAGSystem(config)
rag.build_knowledge(
    file_paths=[
        "e:/github_project/mcp_rag_llm/mcp_rag_langchain/db/rag_db/doupocangqiong.txt"
    ]
)

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("rag")

@mcp.tool()
async def rag_query(query):
    """为斗破苍穹小说提供相关的知识补充
    :param query:
    :return:
    """
    response = rag.query(query)
    return response["answer"]


async def search_demo():
    query = "萧炎的女性朋友有那些?"
    response = await rag_query(query)
    print("response:",response)

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='RAG Server - 基于向量数据库的智能问答系统',
        epilog='''
使用示例:
    1. 启动服务器模式:
        python rag_server_v2.py --mode server
        # 或默认启动服务器模式
        python rag_server_v2.py
    
    2. 运行测试模式:
        python rag_server_v2.py --mode test
        
    3. 自定义测试查询:
        python rag_server_v2.py --mode test --query "萧炎的父亲是谁?"

两种模式的区别:
    - server模式: 启动MCP服务器，等待客户端连接，用于与其他系统集成
    - test模式: 直接执行查询并显示结果，用于快速测试功能
        '''
    )
    parser.add_argument('--mode', type=str, choices=['server', 'test'], default='server',
                      help='运行模式：server(启动服务器)或test(运行测试)')
    parser.add_argument('--query', type=str, default='萧炎的女性朋友有那些?',
                      help='测试模式下的查询语句')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        '''启动MCP服务器，用于与客户端联调''' 
        print("启动RAG MCP服务器...")
        mcp.run(transport="stdio")
    else:
        '''运行测试模式，直接执行查询'''        
        print(f"运行RAG测试查询: {args.query}")
        response = asyncio.run(rag_query(args.query))
        print("\n测试结果:")
        print(response)