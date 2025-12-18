from modelscope import snapshot_download
import inspect

# 查看snapshot_download函数的参数
print(inspect.signature(snapshot_download))

# 下载bge-large-zh-v1.5模型
model_dir = snapshot_download(
    "AI-ModelScope/bge-large-zh-v1.5",
    revision="master",
    cache_dir=r"E:\github_project\models",
    local_dir=r"E:\github_project\models\bge-large-zh-v1.5-2"
)

print(f"模型下载完成，保存路径: {model_dir}")
