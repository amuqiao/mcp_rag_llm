from modelscope import snapshot_download
import inspect

# 查看snapshot_download函数的参数
print(inspect.signature(snapshot_download))

# 下载bge-reranker-large模型
model_dir = snapshot_download(
    "Xorbits/bge-reranker-large",
    revision="master",
    cache_dir=r"E:\github_project\models",
    local_dir=r"E:\github_project\models\bge-reranker-large-2"
)

print(f"模型下载完成，保存路径: {model_dir}")
