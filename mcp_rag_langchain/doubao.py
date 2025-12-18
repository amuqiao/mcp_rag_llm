# -*- encoding: utf-8 -*-
"""
1.索引的构建
2.server服务的封装，mcp的封装
"""
import asyncio
import os
from dotenv import load_dotenv

# 修正导入路径（核心修复点）
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings

load_dotenv()


class RAGSystem(object):
    def __init__(self, config):
        self.config = config
        # 初始化大模型
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "qwen-plus"),
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
            temperature=0.1  # 新增：降低随机性，提升回答准确性
        )
        # 初始化嵌入模型（新增model_kwargs避免设备警告）
        self.embedding = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBED_MODEL"),
            model_kwargs={"device": "cpu"},  # 指定CPU运行（根据需求改cuda）
            encode_kwargs={"normalize_embeddings": True}
        )
        # 初始化向量库（新版本Chroma无需手动persist）
        self.vectorstore = Chroma(
            collection_name=self.config["collection_name"],
            embedding_function=self.embedding,
            persist_directory=self.config["persist_dir"]
        )
        # 初始化检索器
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": self.config.get("top_k", 5)
            }
        )

    def _load_documents(self, file_paths):
        """加载文档（兼容PDF/TXT）"""
        docs = []
        for path in file_paths:
            # 检查文件是否存在
            if not os.path.exists(path):
                print(f"警告：文件不存在，跳过 -> {path}")
                continue
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.endswith(".txt"):
                loader = TextLoader(path, encoding="utf-8")
            else:
                print(f"警告：不支持的文件格式，跳过 -> {path}")
                continue
            docs.extend(loader.load())
        return docs

    def _chunk_documents(self, docs):
        """文档分块"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.get("chunk_size", 500),
            chunk_overlap=self.config.get("chunk_overlap", 50),
            length_function=len,
            is_separator_regex=False  # 修正：默认False更通用，避免正则分割异常
        )
        return text_splitter.split_documents(docs)

    def build_knowledge(self, file_paths):
        """构建知识库"""
        # 1.加载文档
        raw_docs = self._load_documents(file_paths)
        if not raw_docs:
            print("警告：未加载到任何文档，跳过知识库构建")
            return

        # 2.切分文档
        chunks = self._chunk_documents(docs=raw_docs)
        if not chunks:
            print("警告：文档分块后为空，跳过知识库构建")
            return

        # 3.生成向量并存储（新版本Chroma自动持久化，无需调用persist()）
        self.vectorstore.add_documents(chunks)
        print(f"知识库构建完成，文档块数为：{len(chunks)}")

    def query(self, question):
        """问答查询"""
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriever,
            return_source_documents=True,
            chain_type="stuff"  # 显式指定chain_type，避免默认值兼容问题
        )
        # 核心修复：v1.x中invoke入参从query改为input
        result = qa_chain.invoke({"input": question})
        return_result = {
            "answer": result["result"],
            "sources": [
                {
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", "N/A")
                }
                for doc in result["source_documents"]
            ]
        }
        return return_result


# 配置项
config = {
    "persist_dir": "./data/rag_db",
    "collection_name": "rag",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 5
}

# 初始化RAG系统并构建知识库
rag = RAGSystem(config)
rag.build_knowledge(
    file_paths=[
        "./data/doupocangqiong.txt"  # 确保该文件存在
    ]
)

# MCP服务封装
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("rag")

    @mcp.tool()
    async def rag_query(query):
        """为斗破苍穹小说提供相关的知识补充
        :param query: 用户的问题
        :return: 相关回答
        """
        response = rag.query(query)
        return response["answer"]

except ImportError as e:
    print(f"警告：MCP相关模块导入失败 -> {e}")
    rag_query = None


async def search_demo():
    """测试查询"""
    if rag_query is None:
        print("错误：rag_query函数未初始化")
        return
    query = "萧炎的女性朋友有那些?"
    response = await rag_query(query)
    print("问题：", query)
    print("回答：", response)


if __name__ == '__main__':
    # 运行测试
    asyncio.run(search_demo())
    # 如需启动MCP服务，取消注释下面一行
    # if 'mcp' in locals():
    #     asyncio.run(mcp.run(transport="stdio"))