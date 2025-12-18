import torch
from transformers import AutoModel, AutoTokenizer, AutoModelForSequenceClassification, XLMRobertaTokenizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 模型路径（从.env文件中获取的路径）
EMBED_MODEL_PATH = "e:/github_project/models/bge-large-zh-v1.5"
RERANK_MODEL_PATH = "e:/github_project/models/bge-reranker-large"

def load_embedding_model(model_path):
    """加载Embedding模型并验证"""
    try:
        # 方法1：使用sentence-transformers（推荐，对BGE模型有优化）
        model = SentenceTransformer(model_path)
        print("Embedding模型加载成功（sentence-transformers）")
        
        # 验证：生成两个句子的嵌入并计算相似度
        sentences = ["我喜欢吃苹果", "我喜爱食用苹果"]
        embeddings = model.encode(sentences)
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        print(f"Embedding验证 - 相似句子余弦相似度: {similarity:.4f}（预期应较高）")
        
        # 验证不相似句子
        sentences = ["我喜欢吃苹果", "汽车在马路上行驶"]
        embeddings = model.encode(sentences)
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        print(f"Embedding验证 - 不相似句子余弦相似度: {similarity:.4f}（预期应较低）")
        
        return model
    except Exception as e:
        print(f"Embedding模型加载失败: {str(e)}")
        return None

def load_rerank_model(model_path):
    """加载重排序模型并验证"""
    try:
        import os
        print(f"尝试加载Rerank模型，路径: {model_path}")
        
        # 检查目录结构和文件
        if os.path.exists(model_path):
            files = os.listdir(model_path)
            print(f"目录下的文件: {files}")
            
            # 检查必要文件是否存在
            required_files = ['tokenizer_config.json', 'special_tokens_map.json', 'sentencepiece.bpe.model', 'model.safetensors']
            for file in required_files:
                print(f"{file} 存在: {os.path.exists(os.path.join(model_path, file))}")
        else:
            print(f"目录不存在: {model_path}")
        
        # 尝试加载tokenizer
        print("开始加载tokenizer...")
        # 直接使用XLMRobertaTokenizer类而不是AutoTokenizer
        tokenizer = XLMRobertaTokenizer.from_pretrained(
            model_path,
            local_files_only=True
        )
        print("Tokenizer加载成功")
        
        # 尝试加载模型，显式指定模型文件
        model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            local_files_only=True,
            from_tf=False,
            low_cpu_mem_usage=True
        )
        model.eval()  # 切换到评估模式
        print("\nRerank模型加载成功")
        
        # 验证：对句子对进行排序评分
        query = "推荐一款好吃的水果"
        candidates = [
            "苹果是一种营养丰富的水果",
            "汽车维修指南",
            "香蕉富含钾元素",
            "电脑故障排除方法"
        ]
        
        # 构建句子对
        pairs = [(query, candidate) for candidate in candidates]
        with torch.no_grad():
            inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt", max_length=512)
            outputs = model(**inputs)
            scores = outputs.logits.squeeze().tolist()
        
        # 打印评分结果
        print("Rerank验证 - 句子对评分（分数越高相关性越强）:")
        for candidate, score in zip(candidates, scores):
            print(f"分数: {score:.4f} | 句子: {candidate}")
        
        return model, tokenizer
    except Exception as e:
        print(f"Rerank模型加载失败: {str(e)}")
        return None, None

if __name__ == "__main__":
    # 检查是否有GPU可用
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")
    
    # 加载并验证Embedding模型
    embed_model = load_embedding_model(EMBED_MODEL_PATH)
    
    # 加载并验证Rerank模型
    rerank_model, rerank_tokenizer = load_rerank_model(RERANK_MODEL_PATH)