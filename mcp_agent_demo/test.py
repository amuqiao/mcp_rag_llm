import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    # 从.env文件加载API配置
    api_key=os.environ.get("API_KEY"),
    base_url=os.environ.get("BASE_URL"),
)

completion = client.chat.completions.create(
    model=os.environ.get("MODEL"), # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你是谁？'}
        ]
)
print(completion.choices[0].message.content)