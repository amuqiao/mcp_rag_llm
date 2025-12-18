import asyncio
import os
from dotenv import load_dotenv

# -------------------------- LangChain 1.2+ 核心模块 --------------------------
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# -------------------------- 文档加载与分割 --------------------------
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -------------------------- 向量存储与嵌入 --------------------------
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings

# -------------------------- LLM 模型 --------------------------
from langchain_openai import ChatOpenAI

# -------------------------- MCP 工具封装 --------------------------
from mcp.server.fastmcp import FastMCP

# 加载环境变量（.env 文件需配置 MODEL/BASE_URL/API_KEY/EMBED_MODEL）
load_dotenv()

class RAGSystem:
    def __init__(self, config):
        self.config = config
        # 1. 初始化大语言模型（兼容通义千问等OpenAI兼容接口）
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "qwen-plus"),
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
            temperature=0.1,  # 降低随机性，保证回答准确性
            max_tokens=2048
        )

        # 2. 初始化文本嵌入模型（HuggingFace中文嵌入）
        self.embedding = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBED_MODEL", "text2vec-base-chinese"),
            model_kwargs={"device": "cpu"},  # 可改为"cuda"启用GPU
            encode_kwargs={"normalize_embeddings": True}
        )

        # 3. 初始化Chroma向量库（持久化存储）
        self.vectorstore = Chroma(
            collection_name=self.config["collection_name"],
            embedding_function=self.embedding,
            persist_directory=self.config["persist_dir"]
        )

        # 4. 初始化检索器（MMR算法，top_k控制返回文档数）
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",  # 最大边际相关性，避免文档重复
            search_kwargs={"k": self.config.get("top_k", 5)}
        )

        # 5. 构建基于LCEL的RAG链（核心改造点）
        self._build_lcel_rag_chain()

    def _build_lcel_rag_chain(self):
        """构建LCEL风格的RAG链：检索 → 格式化上下文 → 提示词 → LLM → 解析输出"""
        # 定义专属Prompt模板（适配斗破苍穹问答场景）
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是斗破苍穹小说的专属知识库助手，严格基于以下上下文回答问题，禁止编造信息。"
                "如果上下文无相关信息，直接回答「未找到相关信息」。\n\n上下文：{context}"
            ),
            ("human", "{question}")
        ])

        # 格式化检索到的文档为字符串（供Prompt使用）
        def format_documents(docs):
            return "\n\n".join([f"文档片段：{doc.page_content}" for doc in docs])

        # 构建LCEL链（管道化调用）
        self.rag_chain = (
            # 并行处理：检索上下文 + 透传用户问题 + 保留源文档
            RunnableParallel({
                "context": self.retriever | format_documents,
                "question": RunnablePassthrough(),
                "source_docs": self.retriever  # 保留源文档用于返回溯源信息
            })
            # 生成答案 + 透传源文档
            | {
                "answer": prompt | self.llm | StrOutputParser(),  # 生成并解析回答
                "source_docs": lambda x: x["source_docs"]  # 透传源文档信息
            }
        )

    def _load_documents(self, file_paths):
        """加载文档（支持PDF/TXT）"""
        docs = []
        for path in file_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"文件不存在：{path}")
            
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.endswith(".txt"):
                loader = TextLoader(path, encoding="utf-8")
            else:
                raise ValueError(f"不支持的文件格式：{path}（仅支持PDF/TXT）")
            
            docs.extend(loader.load())
        return docs

    def _chunk_documents(self, docs):
        """文档切块（避免单块过长）"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.get("chunk_size", 500),
            chunk_overlap=self.config.get("chunk_overlap", 50),
            length_function=len,
            is_separator_regex=False  # 关闭正则分割，提升兼容性
        )
        return text_splitter.split_documents(docs)

    def build_knowledge(self, file_paths):
        """构建知识库：加载文档 → 切块 → 存入向量库"""
        # 1. 加载原始文档
        raw_docs = self._load_documents(file_paths)
        if not raw_docs:
            print("⚠️ 未加载到任何文档")
            return
        
        # 2. 文档切块
        chunks = self._chunk_documents(raw_docs)
        if not chunks:
            print("⚠️ 文档切块后为空")
            return
        
        # 3. 存入向量库并持久化
        self.vectorstore.add_documents(chunks)
        self.vectorstore.persist()
        print(f"✅ 知识库构建完成，共存入 {len(chunks)} 个文档块")

    def query(self, question):
        """执行RAG查询（返回答案+源文档溯源）"""
        # 调用LCEL链
        result = self.rag_chain.invoke(question)
        
        # 整理源文档信息
        sources = [
            {
                "source": doc.metadata.get("source", "未知文件"),
                "page": doc.metadata.get("page", "无页码") if "page" in doc.metadata else "无页码"
            }
            for doc in result["source_docs"]
        ]
        
        return {
            "answer": result["answer"],
            "sources": sources
        }

# -------------------------- 配置项 --------------------------
RAG_CONFIG = {
    "persist_dir": "./data/rag_db",  # 向量库持久化目录
    "collection_name": "doupocangqiong",  # 向量库集合名（改为斗破苍穹专属）
    "chunk_size": 500,  # 文档块大小
    "chunk_overlap": 50,  # 文档块重叠长度
    "top_k": 5  # 检索返回最大文档数
}

# -------------------------- 初始化RAG系统 --------------------------
rag = RAGSystem(RAG_CONFIG)

# 首次运行需构建知识库（注释掉已构建的情况）
# rag.build_knowledge(file_paths=["./data/doupocangqiong.txt"])

# -------------------------- MCP工具封装 --------------------------
mcp = FastMCP("doupocangqiong_rag")

@mcp.tool()
async def rag_query(query: str) -> str:
    """
    斗破苍穹小说专属知识查询工具
    :param query: 用户的问题（例如：萧炎的女性朋友有哪些？）
    :return: 基于小说原文的准确回答
    """
    response = rag.query(query)
    return response["answer"]

# -------------------------- 测试Demo --------------------------
async def search_demo():
    """测试RAG查询功能"""
    test_query = "萧炎的女性朋友有哪些？"
    print(f"📝 问题：{test_query}")
    answer = await rag_query(test_query)
    print(f"💡 回答：{answer}")

if __name__ == '__main__':
    # 运行测试Demo
    asyncio.run(search_demo())
    
    # 如需启动MCP服务（通过stdio通信），注释上面一行，取消下面注释
    # mcp.run(transport="stdio")