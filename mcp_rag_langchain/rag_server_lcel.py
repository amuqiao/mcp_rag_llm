# -*- encoding: utf-8 -*-

"""
使用LangChain >1.2.0版本和LCEL实现的RAG系统
1. 索引构建（文档加载、文本分割、向量存储）
2. 使用LCEL构建RAG查询链
3. MCP服务器封装
"""

import asyncio
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class RAGSystemLCEL:
    def __init__(self, config):
        self.config = config
        
        # 初始化LLM
        try:
            self.llm = ChatOpenAI(
                model=os.getenv("MODEL", "qwen-plus"),
                base_url=os.getenv("BASE_URL"),
                api_key=os.getenv("API_KEY"),
                temperature=0.0
            )
            logger.info("LLM初始化成功")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            raise
        
        # 初始化Embedding模型
        try:
            self.embedding = HuggingFaceEmbeddings(
                model_name=os.getenv("EMBED_MODEL", "BAAI/bge-large-zh-v1.5")
            )
            logger.info("Embedding模型初始化成功")
        except Exception as e:
            logger.error(f"Embedding模型初始化失败: {e}")
            raise
        
        # 初始化向量存储
        try:
            self.vectorstore = Chroma(
                collection_name=self.config["collection_name"],
                embedding_function=self.embedding,
                persist_directory=self.config["persist_dir"]
            )
            logger.info("向量存储初始化成功")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {e}")
            raise
        
        # 初始化检索器
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": self.config.get("top_k", 5),
                "fetch_k": 20
            }
        )
        
        # 构建RAG链
        self.rag_chain = self._build_rag_chain()
    
    def _load_documents(self, file_paths):
        """加载文档"""
        docs = []
        for path in file_paths:
            try:
                if path.endswith(".pdf"):
                    loader = PyPDFLoader(path)
                    logger.info(f"加载PDF文档: {path}")
                elif path.endswith(".txt"):
                    loader = TextLoader(path, encoding="utf-8")
                    logger.info(f"加载TXT文档: {path}")
                else:
                    logger.warning(f"跳过不支持的文件格式: {path}")
                    continue
                    
                docs.extend(loader.load())
            except Exception as e:
                logger.error(f"加载文档 {path} 失败: {e}")
                continue
        return docs
    
    def _chunk_documents(self, docs):
        """文档分块"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.get("chunk_size", 500),
            chunk_overlap=self.config.get("chunk_overlap", 50),
            length_function=len,
            is_separator_regex=True
        )
        return text_splitter.split_documents(docs)
    
    def _build_rag_chain(self):
        """使用LCEL构建RAG链"""
        # 定义提示模板
        prompt = ChatPromptTemplate.from_template(
            """你是一个知识渊博的助手，根据提供的上下文回答用户问题。
请确保你的回答完全基于提供的上下文信息，不要添加任何外部知识。
如果上下文信息不足以回答问题，请明确说明。

上下文:
{context}

用户问题:
{question}

回答:
"""
        )
        
        # 定义上下文格式化函数
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        # 使用LCEL构建链
        rag_chain = (
            {
                "context": self.retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        logger.info("RAG链构建完成")
        return rag_chain
    
    def build_knowledge(self, file_paths):
        """构建知识库"""
        try:
            # 1. 加载文档
            logger.info("开始加载文档...")
            raw_docs = self._load_documents(file_paths)
            if not raw_docs:
                logger.warning("没有加载到任何文档")
                return
            
            # 2. 文档分块
            logger.info(f"开始文档分块，原始文档数: {len(raw_docs)}")
            chunks = self._chunk_documents(docs=raw_docs)
            logger.info(f"文档分块完成，共 {len(chunks)} 个文档块")
            
            # 3. 向量存储
            logger.info("开始将文档块添加到向量存储...")
            self.vectorstore.add_documents(chunks)
            self.vectorstore.persist()
            logger.info(f"知识库构建完成，文档块数: {len(chunks)}")
        except Exception as e:
            logger.error(f"知识库构建失败: {e}")
            raise
    
    def query(self, question):
        """查询RAG系统"""
        try:
            logger.info(f"处理查询: {question}")
            
            # 使用LCEL链查询
            result = self.rag_chain.invoke(question)
            
            # 获取源文档
            source_docs = self.retriever.invoke(question)
            sources = [
                {
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", "N/A")
                }
                for doc in source_docs
            ]
            
            return_result = {
                "answer": result,
                "sources": sources
            }
            
            logger.info("查询处理完成")
            return return_result
        except Exception as e:
            logger.error(f"查询处理失败: {e}")
            return {
                "answer": f"查询处理失败: {str(e)}",
                "sources": []
            }

# 配置信息
config = {
    "persist_dir": "./data/rag_db",
    "collection_name": "rag_lcel",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 5
}

# 初始化RAG系统
logger.info("初始化RAG系统...")
rag = RAGSystemLCEL(config)

# 构建知识库
# 注意：确保文件路径正确
# rag.build_knowledge(
#     file_paths=[
#         "./data/doupocangqiong.txt"
#     ]
# )

# 导入MCP服务器
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("rag")

@mcp.tool()
async def rag_query(query):
    """为斗破苍穹小说提供相关的知识补充
    :param query: 用户查询的问题
    :return: 查询结果
    """
    response = rag.query(query)
    return response["answer"]


async def search_demo():
    """演示查询功能"""
    query = "萧炎的女性朋友有哪些?"
    logger.info(f"演示查询: {query}")
    response = await rag_query(query)
    logger.info(f"查询结果: {response}")
    print("\n演示查询结果:")
    print(f"问题: {query}")
    print(f"答案: {response}")


if __name__ == '__main__':
    # 运行演示
    asyncio.run(search_demo())
    # 启动MCP服务器
    # mcp.run(transport="stdio")