# MCP RAG LLM 服务运行与测试指南

## 服务独立性分析

项目中包含三个主要服务组件，它们在架构上是相互独立的，可以单独部署和运行：

### 1. MCP RAG Agent (mcp_rag_agent/)
- **核心功能**：提供基于MCP的基础代理服务，包含客户端连接和天气查询功能
- **技术栈**：Python + MCP (Message Channel Protocol) + OpenAI API
- **独立性**：完全独立的服务，不依赖其他两个服务组件

### 2. MCP RAG Agent with GraphRAG (mcp_rag_agent_graphrag/)
- **核心功能**：扩展了基础MCP代理，整合GraphRAG实现更高级的知识图谱检索
- **技术栈**：Python + MCP + OpenAI API + GraphRAG
- **独立性**：独立服务，包含自己的MCP代理实现和GraphRAG组件

### 3. MCP RAG LangChain (mcp_rag_langchain/)
- **核心功能**：基于LangChain的RAG系统，提供文档处理和查询能力
- **技术栈**：Python + LangChain + Chroma + OpenAI API
- **独立性**：独立服务，使用LangChain生态系统实现RAG功能

## 服务运行步骤

### 环境准备

1. **Python环境**：确保安装Python 3.8+版本

2. **依赖安装**：
   ```bash
   # 安装基础依赖
   pip install openai mcp
   
   # 安装LangChain相关依赖（仅用于mcp_rag_langchain）
   pip install langchain langchain-openai chromadb tiktoken
   
   # 安装GraphRAG相关依赖（仅用于mcp_rag_agent_graphrag）
   pip install graphrag
   ```

3. **API配置**：
   - 在各服务目录下创建或修改`.env`文件，配置API密钥
   - 例如，在`mcp_rag_agent_graphrag/mcp_graphrag/.env`中：
     ```
     BASE_URL = https://dashscope.aliyuncs.com/compatible-mode/v1
     API_KEY = your_api_key_here
     MODEL = qwen-plus
     ```

### 1. 运行 MCP RAG Agent 服务

#### 服务端启动：
```bash
cd mcp_rag_agent/mcp_agent
python server.py
```
- 服务将在默认端口启动
- 提供天气查询工具：`query_weather`

#### 客户端使用：
```bash
cd mcp_rag_agent/mcp_agent
python client.py
```
- 客户端将连接到本地服务端
- 可以通过输入查询与代理交互

### 2. 运行 MCP RAG Agent with GraphRAG 服务

#### 服务端启动：
```bash
cd mcp_rag_agent_graphrag/mcp_graphrag
python graphrag_server.py
```
- 启动基于GraphRAG的本地搜索引擎
- 提供本地搜索工具：`local_asearch`

#### 客户端使用：
```bash
cd mcp_rag_agent_graphrag/mcp_agent
python client.py
```
- 客户端将连接到本地GraphRAG服务
- 可以查询斗破苍穹小说的相关知识

### 3. 运行 MCP RAG LangChain 服务

#### 服务端启动：
```bash
cd mcp_rag_langchain
python rag_server.py
```
- 启动基于LangChain的RAG系统
- 加载文档并创建向量存储
- 提供RAG查询工具：`rag_query`

#### 客户端使用：
```bash
cd mcp_rag_langchain
python rag_agent.py
```
- 客户端将连接到本地RAG服务
- 可以查询文档内容

## 服务测试步骤

### 1. MCP RAG Agent 测试

#### 单元测试：
```bash
cd mcp_rag_agent/mcp_agent
python test.py
```
- 测试基本的OpenAI API连接

#### 集成测试：
1. 启动服务端：`python server.py`
2. 在另一个终端启动客户端：`python client.py`
3. 测试天气查询功能：
   ```
   请输入你的查询: 北京的天气怎么样？
   ```

### 2. MCP RAG Agent with GraphRAG 测试

#### 集成测试：
1. 确保GraphRAG数据已准备好（doupocangqiong目录下有预处理数据）
2. 启动GraphRAG服务端：`python graphrag_server.py`
3. 在另一个终端启动客户端：`python client.py`
4. 测试小说知识查询：
   ```
   请输入你的查询: 萧炎的斗气等级是什么？
   ```

### 3. MCP RAG LangChain 测试

#### 集成测试：
1. 准备测试文档（在rag_server.py中配置文档路径）
2. 启动RAG服务端：`python rag_server.py`
3. 在另一个终端启动客户端：`python rag_agent.py`
4. 测试文档查询：
   ```
   请输入你的查询: 文档中关于X的内容是什么？
   ```

## 服务间协作示例

虽然三个服务相互独立，但它们可以通过MCP协议进行协作。以下是一个简单的协作示例：

1. 启动所有三个服务端
2. 修改客户端代码，使其能够连接到多个服务端
3. 实现跨服务的查询路由逻辑

```python
# 示例：连接到多个服务端的客户端代码
from mcp_rag_agent.mcp_agent.client import MCPClient as BasicClient
from mcp_rag_agent_graphrag.mcp_agent.client import MCPClient as GraphragClient
from mcp_rag_langchain.rag_agent import MCPClient as LangchainClient

# 连接到不同服务端
basic_client = BasicClient("http://localhost:8000")
graphrag_client = GraphragClient("http://localhost:8001")
langchain_client = LangchainClient("http://localhost:8002")

# 根据查询类型选择合适的服务
def query_router(query):
    if "天气" in query:
        return basic_client.query(query)
    elif "斗破苍穹" in query or "小说" in query:
        return graphrag_client.query(query)
    else:
        return langchain_client.query(query)
```

## 常见问题与解决方案

### 1. API密钥配置错误
**问题**：客户端连接失败，提示API密钥错误
**解决方案**：
- 检查.env文件中的API_KEY配置是否正确
- 确保API_KEY有足够的权限访问相应的模型服务
- 检查BASE_URL是否指向正确的API端点

### 2. 服务端口冲突
**问题**：服务启动失败，提示端口已被占用
**解决方案**：
- 修改server.py中的端口配置
- 使用lsof命令查看端口占用情况：`lsof -i :8000`
- 终止占用端口的进程：`kill <PID>`

### 3. 依赖安装失败
**问题**：pip安装依赖时出现错误
**解决方案**：
- 确保使用最新版本的pip：`pip install --upgrade pip`
- 使用虚拟环境隔离依赖：`python -m venv venv && source venv/bin/activate`
- 尝试使用镜像源安装：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>`

## 测试结果验证

运行测试后，可以通过以下方式验证结果：

1. **天气查询服务**：
   - 预期输出：包含温度、天气状况、湿度等信息的格式化响应

2. **GraphRAG服务**：
   - 预期输出：基于斗破苍穹小说内容的准确回答
   - 验证：检查回答是否与小说内容一致

3. **LangChain RAG服务**：
   - 预期输出：基于加载文档的相关回答
   - 验证：检查回答是否包含文档中的相关信息

## 总结

项目中的三个服务组件是相互独立的，可以单独运行和测试。每个服务都有自己的客户端和服务端实现，使用MCP协议进行通信。通过本指南，您应该能够成功运行和测试这些服务，并了解它们的工作原理和协作方式。