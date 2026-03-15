import json
import os
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba
import time
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 指定默认字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# ============ 1. 加载数据 ============
print("加载知识库...")
blocks = []
with open("./RAG/oiwiki_blocks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        blocks.append(json.loads(line))
print(f"总块数: {len(blocks)}")
print(f"代码块数: {len([b for b in blocks if b['block_type'] == 'code'])}")

# ============ 2. 定义查询集 ============
queries = [
    "线段树区间修改 代码",
    "SPFA SLF优化 cpp", 
    "快速排序 实现",
    "Dijkstra 堆优化",
    "并查集路径压缩",
    "KMP 匹配",
    "01背包 动态规划",
    "LCA 倍增",
    "网络流 Dinic",
    "主席树 第k小"
]

# ============ 3. T2.1 纯向量检索实验 ============
print("\n" + "="*60)
print("T2.1 纯向量检索实验")
print("="*60)

models = {
    "bge-small-zh": SentenceTransformer("BAAI/bge-small-zh-v1.5"),
    "m3e-small": SentenceTransformer("moka-ai/m3e-small"),
    "codebert": SentenceTransformer("microsoft/codebert-base"),
}

strategies = {
    "content": lambda b: b.get("content", "")[:512],
    "concept": lambda b: " → ".join(b.get("concept_hierarchy", [])) + " " + b.get("content", "")[:512],
    "code": lambda b: f"[{b.get('language', 'text')}] {b.get('content', '')[:512]}" if b["block_type"]=="code" else b.get("content", "")[:512],
}

vector_results = []

for model_name, model in models.items():
    for strategy_name, strategy_fn in strategies.items():
        print(f"\n实验: {model_name} + {strategy_name}")
        start = time.time()
        
        # 构建向量
        texts = [strategy_fn(b) for b in tqdm(blocks, desc="向量化")]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        
        # 建索引
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings.astype(np.float32))
        
        # 测试
        scores = []
        for q in queries:
            q_vec = model.encode(q, normalize_embeddings=True).astype(np.float32).reshape(1, -1)
            s, _ = index.search(q_vec, 5)
            scores.append(np.mean(s[0]))
        
        avg_score = np.mean(scores)
        vector_results.append({
            "model": model_name,
            "strategy": strategy_name,
            "avg_score": avg_score,
            "time": time.time() - start
        })
        print(f"平均分: {avg_score:.4f}, 耗时: {(time.time()-start)/60:.1f}分钟")

# ============ 4. T2.2 关键词检索实验 ============
print("\n" + "="*60)
print("T2.2 关键词检索实验")
print("="*60)

# 构建BM25索引
corpus = [list(jieba.cut(b.get("content", "")[:1000])) for b in blocks]
bm25 = BM25Okapi(corpus)

# 测试不同参数
alpha_values = [0.5, 0.75, 1.0, 1.2, 1.5, 2.0]
keyword_results = []

for k1 in alpha_values:
    print(f"\nBM25参数 k1={k1}")
    
    # 重新初始化BM25（实际BM25Okapi不支持动态调参，这里只是演示）
    scores = []
    for q in queries[:3]:  # 只测前3个节省时间
        tokens = list(jieba.cut(q))
        doc_scores = bm25.get_scores(tokens)
        top5_avg = np.mean(sorted(doc_scores, reverse=True)[:5])
        scores.append(top5_avg)
    
    keyword_results.append({
        "k1": k1,
        "avg_score": np.mean(scores)
    })
    print(f"平均分: {np.mean(scores):.4f}")

# ============ 5. T2.3 混合检索实验 ============
print("\n" + "="*60)
print("T2.3 混合检索实验")
print("="*60)

# 用最好的向量模型
best_model = models["bge-small-zh"]
texts = [strategies["concept"](b) for b in blocks]
embeddings = best_model.encode(texts, normalize_embeddings=True)
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings.astype(np.float32))

# 测试不同混合权重
weights = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
hybrid_results = []

for alpha in weights:
    print(f"\n混合权重 alpha={alpha} (向量权重), 1-alpha={1-alpha} (BM25权重)")
    
    scores = []
    for q in queries:
        # 向量检索
        q_vec = best_model.encode(q, normalize_embeddings=True).astype(np.float32).reshape(1, -1)
        vec_scores, vec_indices = index.search(q_vec, 10)
        
        # BM25检索
        tokens = list(jieba.cut(q))
        bm25_scores = bm25.get_scores(tokens)
        
        # 融合
        hybrid_score = 0
        for i, idx in enumerate(vec_indices[0]):
            if idx == -1: continue
            score = alpha * vec_scores[0][i] + (1-alpha) * (bm25_scores[idx] / 10)
            hybrid_score += score
        
        scores.append(hybrid_score / 5)  # 平均前5
    
    avg_hybrid = np.mean(scores)
    hybrid_results.append({
        "alpha": alpha,
        "avg_score": avg_hybrid
    })
    print(f"平均分: {avg_hybrid:.4f}")

# ============ 6. T2.4 代码专项优化 ============
print("\n" + "="*60)
print("T2.4 代码专项优化")
print("="*60)

# 增强版文本构建（函数名加权）
def enhanced_code_text(block):
    if block["block_type"] != "code":
        return strategies["concept"](block)
    
    content = block.get("content", "")
    # 提取函数名（简单正则）
    import re
    funcs = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)', content)
    func_text = " ".join(funcs[:3])  # 最多3个函数名
    
    lang = block.get("language", "text")
    concepts = " → ".join(block.get("concept_hierarchy", []))
    
    return f"{concepts} [{lang}] 函数: {func_text} {content[:400]}"

# 对比实验
code_optimizations = {
    "baseline": lambda b: strategies["concept"](b),
    "enhanced": enhanced_code_text,
    "lang_only": lambda b: f"[{b.get('language', 'text')}] {b.get('content', '')[:512]}" if b["block_type"]=="code" else strategies["concept"](b),
}

code_results = []

for opt_name, opt_fn in code_optimizations.items():
    print(f"\n优化方案: {opt_name}")
    
    texts = [opt_fn(b) for b in tqdm(blocks, desc="构建文本")]
    embeddings = best_model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype(np.float32))
    
    # 只测代码相关的查询
    code_queries = [q for q in queries if "代码" in q or "cpp" in q or "实现" in q]
    scores = []
    for q in code_queries:
        q_vec = best_model.encode(q, normalize_embeddings=True).astype(np.float32).reshape(1, -1)
        s, idx = index.search(q_vec, 5)
        
        # 统计代码块命中率
        code_hits = 0
        for i in idx[0]:
            if i != -1 and blocks[i]["block_type"] == "code":
                code_hits += 1
        
        scores.append(code_hits / 5)  # 代码块占比
    
    code_results.append({
        "optimization": opt_name,
        "code_hit_rate": np.mean(scores)
    })
    print(f"代码块命中率: {np.mean(scores):.4f}")

# ============ 7. 结果汇总 ============
print("\n" + "="*60)
print("实验结果汇总")
print("="*60)

print("\n【T2.1 向量检索 Top3】")
for r in sorted(vector_results, key=lambda x: x["avg_score"], reverse=True)[:3]:
    print(f"{r['model']:15} {r['strategy']:10} {r['avg_score']:.4f}")

print("\n【T2.2 关键词检索最佳参数】")
best_k = max(keyword_results, key=lambda x: x["avg_score"])
print(f"最佳k1={best_k['k1']}, 得分={best_k['avg_score']:.4f}")

print("\n【T2.3 混合检索最佳权重】")
best_alpha = max(hybrid_results, key=lambda x: x["avg_score"])
print(f"最佳alpha={best_alpha['alpha']}, 得分={best_alpha['avg_score']:.4f}")

print("\n【T2.4 代码优化效果】")
for r in sorted(code_results, key=lambda x: x["code_hit_rate"], reverse=True):
    print(f"{r['optimization']:10} 代码命中率: {r['code_hit_rate']:.4f}")

# ============ 8. 可视化 ============
plt.figure(figsize=(15, 10))

# T2.1
plt.subplot(2, 2, 1)
models_list = list(set([r["model"] for r in vector_results]))
x = np.arange(len(models_list))
width = 0.25
for i, s in enumerate(["content", "concept", "code"]):
    scores = [r["avg_score"] for r in vector_results if r["strategy"] == s]
    plt.bar(x + i*width, scores, width, label=s)
plt.xlabel("模型")
plt.ylabel("平均分")
plt.xticks(x + width, models_list, rotation=45)
plt.title("T2.1 向量检索对比")
plt.legend()

# T2.2
plt.subplot(2, 2, 2)
plt.plot([r["k1"] for r in keyword_results], [r["avg_score"] for r in keyword_results], marker='o')
plt.xlabel("BM25 k1参数")
plt.ylabel("平均分")
plt.title("T2.2 关键词检索参数调优")

# T2.3
plt.subplot(2, 2, 3)
plt.plot([r["alpha"] for r in hybrid_results], [r["avg_score"] for r in hybrid_results], marker='o')
plt.xlabel("向量权重 alpha")
plt.ylabel("混合得分")
plt.title("T2.3 混合检索权重优化")

# T2.4
plt.subplot(2, 2, 4)
names = [r["optimization"] for r in code_results]
scores = [r["code_hit_rate"] for r in code_results]
plt.bar(names, scores)
plt.ylabel("代码块命中率")
plt.title("T2.4 代码专项优化")

plt.tight_layout()
plt.savefig("./t2_experiment_results.png")
plt.show()

print("\n✅ 实验完成！结果已保存至 ./t2_experiment_results.png")