# MCP Agent Demo 项目架构分析

## 1. 项目概述

MCP Agent Demo是一个基于MCP（Model Context Protocol）协议的智能代理系统，主要实现了天气查询功能。该系统采用客户端-服务器架构，通过大语言模型（LLM）驱动工具调用，实现了自然语言到工具执行的无缝转换。

**核心功能**：
- 基于MCP协议的客户端-服务器通信
- 大语言模型驱动的动态工具调用
- 外部Weather API集成
- 异步编程模型

**技术栈**：
- Python 3.x
- MCP协议
- OpenAI API
- WeatherAPI.com
- Asyncio & Httpx
- 命令行交互

## 2. 模块分析

### 2.1 服务器模块 (server.py)

**核心功能**：提供基于MCP协议的天气查询工具服务。

**关键组件**：
- `FastMCP`：MCP服务器实例，用于注册和提供工具
- `get_weather()`：异步调用WeatherAPI获取天气数据
- `format_data()`：格式化天气API响应为友好文本
- `query_weather()`：MCP工具，作为客户端调用的入口

**实现细节**：
```python
@mcp.tool()
async def query_weather(city: str) -> str:
    """
    输入指定的城市名(英文)，返回今日天气情况
    :param city: 城市名称(需使用英文)
    :return: 格式化之后的天气信息
    """
    data = await get_weather(city)
    weather_info = await format_data(json_data=data)
    print("weather_info:", weather_info)
    return weather_info
```

**运行模式**：
- `server`：启动MCP服务器，等待客户端连接
- `test`：直接执行天气查询并显示结果，用于快速测试

### 2.2 客户端模块 (client.py)

**核心功能**：处理用户输入，与LLM交互，调用服务器提供的工具。

**关键组件**：
- `MCPClient`：客户端主类，管理服务器连接和工具调用
- `connect_server()`：连接到MCP服务器
- `process_query()`：处理用户查询，与LLM交互并调用工具
- `chat()`：提供命令行交互界面

**实现细节**：
```python
async def process_query(self, query):
    messages = [{"role": "user", "content": query}]
    tools_info = await self.session.list_tools()
    
    # 构建工具列表
    available_tools = [{"type": "function", "function": {"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema}} for tool in tools_info.tools]
    
    # 与LLM交互
    response = self.client.chat.completions.create(model=self.model, messages=messages, tools=available_tools)
    
    # 处理工具调用
    if response.choices[0].finish_reason == "tool_calls":
        tool_call = message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        # 调用服务器工具
        result = await self.session.call_tool(tool_name, tool_args)
        
        # 将工具结果返回给LLM
        messages.append(message.model_dump())
        messages.append({"role": "tool", "content": result.content[0].text, "tool_call_id": tool_call.id})
        response = self.client.chat.completions.create(model=self.model, messages=messages)
        return response.choices[0].message.content
```

### 2.3 启动模块 (run.py)

**核心功能**：协调客户端和服务器的启动流程。

**实现细节**：
```python
def main():
    # 构建client.py和server.py的绝对路径
    client_path = os.path.join(script_dir, "client.py")
    server_path = os.path.join(script_dir, "server.py")
    
    # 执行命令: python client.py server.py
    command = [sys.executable, client_path, server_path]
    
    print("正在启动客户端并连接到服务器...")
    subprocess.run(command, check=True)
```

### 2.4 测试模块 (test.py)

**核心功能**：验证LLM连接是否正常工作。

**实现细节**：
```python
completion = client.chat.completions.create(
    model=os.environ.get("MODEL"),
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你是谁？'}
        ]
)
print(completion.choices[0].message.content)
```

## 3. 交互关系

### 3.1 模块间依赖关系

```mermaid
graph TD
    A[run.py] --> B[client.py]
    B --> C[server.py]
    B --> D[OpenAI API]
    C --> E[WeatherAPI.com]
    B --> F[.env 配置]
    C --> F
    G[test.py] --> D
    G --> F
    
    style A fill:#FF6B6B,stroke:#2D3436,stroke-width:3px,color:white
    style B fill:#4ECDC4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style C fill:#45B7D1,stroke:#2D3436,stroke-width:2px,color:white
    style D fill:#96CEB4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style E fill:#FF9FF3,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style F fill:#54A0FF,stroke:#2D3436,stroke-width:2px,color:white
    style G fill:#FECA57,stroke:#2D3436,stroke-width:2px,color:#2D3436
```

### 3.2 系统架构图

```mermaid
graph LR
    subgraph 用户交互层
        A[用户命令行] -->|输入查询| B[client.py]
        B -->|输出结果| A
    end
    
    subgraph 客户端层
        B -->|1. 构建工具列表| C[MCPClient]
        C -->|2. 发送请求| D[OpenAI API]
        D -->|3. 返回工具调用| C
        C -->|4. 执行工具调用| E[MCP客户端]
    end
    
    subgraph 服务器层
        E -->|5. 调用工具| F[MCP服务器]
        F -->|6. 执行查询| G[server.py]
        G -->|7. 调用API| H[WeatherAPI.com]
        H -->|8. 返回天气数据| G
        G -->|9. 格式化数据| F
        F -->|10. 返回结果| E
    end
    
    C -->|11. 发送工具结果| D
    D -->|12. 生成最终响应| C
    
    style A fill:#FF6B6B,stroke:#2D3436,stroke-width:3px,color:white
    style B fill:#4ECDC4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style C fill:#45B7D1,stroke:#2D3436,stroke-width:2px,color:white
    style D fill:#96CEB4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style E fill:#FF9FF3,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style F fill:#54A0FF,stroke:#2D3436,stroke-width:2px,color:white
    style G fill:#FECA57,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style H fill:#E9ECEF,stroke:#2D3436,stroke-width:3px,color:#2D3436
```

## 4. 数据流向与控制流程

### 4.1 主要数据流向

```mermaid
sequenceDiagram
    participant User as 用户
    participant Client as 客户端(client.py)
    participant LLM as 大语言模型
    participant MCP as MCP协议层
    participant Server as 服务器(server.py)
    participant WeatherAPI as 天气API
    
    User->>Client: 输入查询(如: "深圳天气如何？")
    Client->>LLM: 发送查询和可用工具列表
    LLM->>Client: 返回工具调用决策
    Client->>MCP: 发送工具调用请求
    MCP->>Server: 转发工具调用
    Server->>WeatherAPI: 调用外部天气API
    WeatherAPI->>Server: 返回天气数据
    Server->>MCP: 返回格式化的天气信息
    MCP->>Client: 转发工具调用结果
    Client->>LLM: 发送工具调用结果
    LLM->>Client: 生成自然语言响应
    Client->>User: 显示最终结果
```

### 4.2 工具调用流程

```mermaid
flowchart LR
    A[用户输入查询] --> B[客户端构建消息]
    B --> C[客户端获取可用工具列表]
    C --> D[发送请求到LLM]
    D --> E{LLM决策}
    E -->|需要工具调用| F[解析工具调用参数]
    F --> G[通过MCP调用服务器工具]
    G --> H[服务器执行工具]
    H --> I[调用外部API]
    I --> J[格式化返回结果]
    J --> K[返回工具执行结果]
    K --> L[将结果发送回LLM]
    L --> M[LLM生成最终响应]
    M --> N[返回结果给用户]
    E -->|直接回答| M
    
    style A fill:#FF6B6B,stroke:#2D3436,stroke-width:3px,color:white
    style B fill:#4ECDC4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style C fill:#45B7D1,stroke:#2D3436,stroke-width:2px,color:white
    style D fill:#96CEB4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style E fill:#FF9FF3,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style F fill:#54A0FF,stroke:#2D3436,stroke-width:2px,color:white
    style G fill:#FECA57,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style H fill:#E9ECEF,stroke:#2D3436,stroke-width:3px,color:#2D3436
    style I fill:#FF6B6B,stroke:#2D3436,stroke-width:3px,color:white
    style J fill:#4ECDC4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style K fill:#45B7D1,stroke:#2D3436,stroke-width:2px,color:white
    style L fill:#96CEB4,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style M fill:#FF9FF3,stroke:#2D3436,stroke-width:2px,color:#2D3436
    style N fill:#54A0FF,stroke:#2D3436,stroke-width:2px,color:white
```

## 5. 系统特性与设计亮点

### 5.1 MCP协议的优势

- **动态工具发现**：客户端可以自动发现服务器提供的所有工具
- **标准化通信**：采用统一的协议格式，便于扩展和集成
- **异步支持**：完全支持异步编程模型，提高系统性能

### 5.2 架构设计亮点

1. **分层架构**：清晰的用户交互层、客户端层和服务器层分离
2. **松耦合设计**：各模块之间通过明确的接口通信，便于维护和扩展
3. **配置驱动**：通过.env文件统一管理配置，便于部署和管理
4. **错误处理**：完善的异常处理机制，提高系统稳定性
5. **测试友好**：提供多种运行模式和测试工具，便于开发和调试

## 6. 总结

MCP Agent Demo是一个基于MCP协议的智能代理系统，通过客户端-服务器架构实现了大语言模型与外部工具的无缝集成。系统的核心价值在于：

1. **自然语言驱动**：用户可以通过自然语言查询天气信息
2. **动态工具调用**：LLM可以根据用户需求动态选择合适的工具
3. **模块化设计**：清晰的模块划分，便于维护和扩展
4. **异步性能**：采用异步编程模型，提高系统响应速度

该项目展示了如何将大语言模型与外部API集成，实现智能代理系统的设计和开发，为构建更复杂的智能应用提供了参考架构。