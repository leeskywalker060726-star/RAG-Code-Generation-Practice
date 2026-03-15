#T1.3
import json
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
import jieba
from sentence_transformers import SentenceTransformer

# 1. 加载模型和索引
print("加载模型...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
index = faiss.read_index("./faiss.index")

with open("./mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)
idx_to_meta = {i: m for i, m in enumerate(mapping)}

# 2. 加载原始块
print("加载知识库...")
blocks_dict = {}
with open("./oiwiki_blocks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        b = json.loads(line)
        blocks_dict[b["id"]] = b

# 3. 构建BM25索引
print("构建BM25索引...")
valid_blocks = [blocks_dict[m["id"]] for m in mapping if m["id"] in blocks_dict]
corpus = [list(jieba.cut(b.get("content", "")[:1000])) for b in valid_blocks]
bm25 = BM25Okapi(corpus)
print(f"BM25索引完成，规模: {len(corpus)}")

# 4. 检索器类
class OIRetriever:
    def __init__(self):
        self.index = index
        self.idx_to_meta = idx_to_meta
        self.blocks_dict = blocks_dict
        self.bm25 = bm25
    
    def search(self, query, top_k=3, alpha=0.6):
        # 向量检索
        query_vec = model.encode(query, normalize_embeddings=True).astype(np.float32).reshape(1, -1)
        vec_scores, vec_indices = self.index.search(query_vec, 30)
        
        # BM25检索
        tokens = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokens)
        bm25_top = np.argsort(bm25_scores)[-30:][::-1]
        
        # 融合得分
        scores_dict = {}
        for idx, score in zip(vec_indices[0], vec_scores[0]):
            if idx != -1:
                scores_dict[idx] = alpha * score
        
        for i, idx in enumerate(bm25_top):
            score = bm25_scores[idx] / 5
            scores_dict[idx] = scores_dict.get(idx, 0) + (1 - alpha) * score
        
        # 排序
        sorted_idx = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # 返回结果
        results = []
        for idx, score in sorted_idx:
            meta = self.idx_to_meta[idx]
            block = self.blocks_dict.get(meta["id"], {})
            results.append({
                "id": meta["id"],
                "score": score,
                "block_type": meta["block_type"],
                "language": meta.get("language"),
                "concept_hierarchy": meta["concept_hierarchy"],
                "file_path": meta["file_path"],
                "content": block.get("content", ""),
                "next_block_id": block.get("next_block_id"),
                "prev_block_id": block.get("prev_block_id")
            })
        return results

# 5. 交互式检索
def interactive_search():
    retriever = OIRetriever()
    print("\n✅ OI-Wiki 检索器已启动，输入 q 退出\n")
    
    while True:
        query = input("🔍 请输入查询: ")
        if query.lower() in ['q', 'quit', 'exit']:
            break
        
        print("\n正在检索...")
        results = retriever.search(query, top_k=3)
        
        # 显示结果列表
        print("\n" + "="*80)
        print("【检索结果】")
        print("="*80)
        for i, r in enumerate(results):
            print(f"\n[{i+1}] 得分: {r['score']:.4f}")
            print(f"    路径: {' → '.join(r['concept_hierarchy'])}")
            print(f"    类型: {r['block_type']} | 语言: {r.get('language', 'unknown')}")
            print(f"    预览: {r['content'][:150].replace(chr(10), ' ')}...")
        
        # 选择结果
        while True:
            choice = input("\n📌 请选择要查看的结果编号 (1-3，输入0重新查询): ")
            if choice == '0':
                break
            if choice in ['1', '2', '3']:
                idx = int(choice) - 1
                current_block = results[idx]
                
                # 显示选中的结果
                print("\n" + "="*80)
                print(f"【选中结果 {choice}】得分: {current_block['score']:.4f}")
                print("="*80)
                print(f"ID: {current_block['id']}")
                print(f"类型: {current_block['block_type']} | 语言: {current_block.get('language', 'unknown')}")
                print(f"路径: {' → '.join(current_block['concept_hierarchy'])}")
                print(f"文件: {current_block['file_path']}")
                print("-"*80)
                print("内容:")
                print(current_block['content'])
                print("-"*80)
                
                # 查看后续块
                current_id = current_block['id']
                history = [current_block['content']]  # 保存历史输出
                
                while True:
                    cmd = input("\n➡️ 输入 y 查看下一个块，输入 n 重新选择结果，输入 q 退出: ")
                    if cmd.lower() == 'y':
                        block_data = retriever.blocks_dict.get(current_id)
                        if block_data and block_data.get('next_block_id'):
                            current_id = block_data['next_block_id']
                            next_block = retriever.blocks_dict.get(current_id, {})
                            history.append(next_block.get('content', ''))
                            
                            # 重新显示所有历史内容
                            print("\n" + "="*80)
                            print(f"【历史内容】已显示 {len(history)} 个连续块")
                            print("="*80)
                            for h_idx, h_content in enumerate(history):
                                print(f"\n--- 块 {h_idx+1} ---")
                                print(h_content)
                                print("-"*40)
                        else:
                            print("⚠️ 没有下一个块了")
                    
                    elif cmd.lower() == 'n':
                        break  # 返回结果选择
                    
                    elif cmd.lower() in ['q', 'quit']:
                        return  # 退出整个程序
                    
                    else:
                        print("无效输入，请输入 y/n/q")
                
            else:
                print("无效输入，请输入1-3")
        
        print("\n" + "-"*80)

# 6. 运行
if __name__ == "__main__":
    interactive_search()