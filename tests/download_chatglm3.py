from modelscope import snapshot_download
import inspect

# 查看snapshot_download函数的参数
print(inspect.signature(snapshot_download))

# 下载完整的ChatGLM3-6B模型
model_dir = snapshot_download(
    "ZhipuAI/chatglm3-6b",
    revision="v1.0.0",
    cache_dir="E:\github_project\models",
    local_dir="E:\github_project\models\chatglm3-6b"
)

print(f"模型下载完成，保存路径: {model_dir}")