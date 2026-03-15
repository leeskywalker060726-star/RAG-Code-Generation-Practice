
import os
import json
import time
import hashlib
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import jieba
from typing import List, Dict, Any, Optional
from pathlib import Path
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
class OIRetrieverAPI:
    """
    OI-Wiki 检索器 API 封装
    
    使用示例：
        from oi_retriever_api import OIRetrieverAPI
        
        # 初始化
        api = OIRetrieverAPI(index_dir="./")
        
        # 搜索
        result = api.search("线段树区间修改", top_k=3)
        for r in result["results"]:
            print(r["concept_hierarchy"], r["score"])
    """
    
    def __init__(self, index_dir: str = "./"):
        """
        初始化检索器
        
        Args:
            index_dir: 索引文件所在目录
        """
        self.index_dir = Path(index_dir)
        self.cache = {}
        self.cache_size = 100
        self.history = []
        
        print("📚 加载知识库...")
        self._load_data()
        print("🧠 加载模型...")
        self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        
        print("🔍 加载索引...")
        self.index = faiss.read_index(str( "./faiss.index"))
        
        with open( "./mapping.json", "r", encoding="utf-8") as f:
            self.mapping = json.load(f)
        self.idx_to_meta = {i: m for i, m in enumerate(self.mapping)}
        
        print("📊 构建BM25索引...")
        self._build_bm25()
        
        print(f"✅ API初始化完成，共 {len(self.blocks_list)} 个块")
    
    def _load_data(self):
        """加载原始数据"""
        self.blocks_list = []
        self.blocks_dict = {}
        
        with open("./oiwiki_blocks.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                b = json.loads(line)
                self.blocks_list.append(b)
                self.blocks_dict[b["id"]] = b
    
    def _build_bm25(self):
        """构建BM25索引"""
        corpus = []
        for b in self.blocks_list:
            content = b.get("content", "")[:1000]
            corpus.append(list(jieba.cut(content)))
        self.bm25 = BM25Okapi(corpus)
    
    def _hybrid_search(self, query: str, top_k: int = 10, alpha: float = 0.3) -> List[tuple]:
        """混合检索"""
        # 向量检索
        q_vec = self.model.encode(query, normalize_embeddings=True).astype(np.float32).reshape(1, -1)
        vec_scores, vec_indices = self.index.search(q_vec, top_k * 3)
        
        # BM25检索
        tokens = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokens)
        bm25_top = np.argsort(bm25_scores)[-top_k*3:][::-1]
        
        # 融合得分
        scores_dict = {}
        for idx, score in zip(vec_indices[0], vec_scores[0]):
            if idx != -1:
                scores_dict[idx] = alpha * score
        
        for idx in bm25_top:
            score = bm25_scores[idx] / 5
            scores_dict[idx] = scores_dict.get(idx, 0) + (1 - alpha) * score
        
        sorted_items = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_k]
    
    def get_line_index(self, block_id: str) -> int:
        """获取块在文件中的行号"""
        for i, block in enumerate(self.blocks_list):
            if block["id"] == block_id:
                return i
        return -1
    
    def search_next_cpp(self, start_line: int) -> Optional[Dict]:
        """从start_line往后找最近的C++代码块"""
        for i in range(start_line + 1, len(self.blocks_list)):
            block = self.blocks_list[i]
            if block.get("block_type") == "code":
                lang = block.get("language", "").lower()
                if lang in ["cpp", "c++", "cc", "hpp"]:
                    return {
                        "line": i,
                        "content": block.get("content", ""),
                        "id": block.get("id"),
                        "language": block.get("language")
                    }
        return None

    def search_next_python(self, start_line: int) -> Optional[Dict]:
        """从start_line往后找最近的Python代码块"""
        for i in range(start_line + 1, len(self.blocks_list)):
            block = self.blocks_list[i]
            if block.get("block_type") == "code":
                lang = block.get("language", "").lower()
                if lang in ["python", "py"]:
                    return {
                        "line": i,
                        "content": block.get("content", ""),
                        "id": block.get("id"),
                        "language": block.get("language")
                    }
        return None
    
    def _get_cache_key(self, query: str, **kwargs) -> str:
        """生成缓存键"""
        key_str = query + str(sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def search(self, 
               query: str, 
               top_k: int = 3,
               mode: str = "standard",
               code_only: bool = False,
               language: Optional[str] = None,
               use_cache: bool = True) -> Dict[str, Any]:
        """
        统一检索接口
        
        Args:
            query: 查询字符串
            top_k: 返回结果数
            mode: 检索模式
                - "standard": 标准模式，只返回检索结果
                - "with_context": 返回结果并自动获取上下文
            code_only: 是否只返回代码块
            language: 按语言过滤（cpp/python等）
            use_cache: 是否使用缓存
        
        Returns:
            {
                "query": query,
                "mode": mode,
                "results": [...],
                "total": 结果数,
                "time_ms": 耗时,
                "cached": 是否来自缓存
            }
        """
        start_time = time.time()
        
        # 缓存检查
        cache_key = self._get_cache_key(query)
        if use_cache and cache_key in self.cache:
            result = self.cache[cache_key]
            result["cached"] = True
            return result
        
        # 执行检索
        candidates = self._hybrid_search(query, top_k=top_k * 2)
        
        # 构建结果
        results = []
        for idx, score in candidates:
            if len(results) >= top_k:
                break
                
            meta = self.idx_to_meta[idx]
            block = self.blocks_dict.get(meta["id"], {})
            
            # 过滤
            if code_only and meta["block_type"] != "code":
                continue
            if language:
                block_lang = meta.get("language", "")
                if block_lang.lower() != language.lower():
                    continue
            
            result_item = {
                "id": meta["id"],
                "score": float(score),
                "block_type": meta["block_type"],
                "language": meta.get("language"),
                "concept_hierarchy": meta["concept_hierarchy"],
                "file_path": meta["file_path"],
                "content": block.get("content", "")[:500],
                "line_index": self.get_line_index(meta["id"])
            }
            
            # 添加上下文
            if mode == "with_context":
                line_idx = result_item["line_index"]
                context = []
                for i in range(max(0, line_idx - 2), min(len(self.blocks_list), line_idx + 3)):
                    if i == line_idx:
                        continue
                    ctx_block = self.blocks_list[i]
                    context.append({
                        "id": ctx_block["id"],
                        "type": ctx_block["block_type"],
                        "language": ctx_block.get("language"),
                        "relation": "prev" if i < line_idx else "next",
                        "preview": ctx_block.get("content", "")[:100]
                    })
                result_item["context"] = context
            
            results.append(result_item)
        
        response = {
            "query": query,
            "mode": mode,
            "results": results,
            "total": len(results),
            "time_ms": int((time.time() - start_time) * 1000),
            "cached": False
        }
        
        # 存入缓存
        if use_cache:
            self.cache[cache_key] = response
            if len(self.cache) > self.cache_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
        
        # 记录历史
        self.history.append({
            "timestamp": time.time(),
            "query": query,
            "result_count": len(results)
        })
        
        return response
    
    def get_next_block(self, block_id: str, direction: str = "next") -> Optional[Dict]:
        """获取当前块的下一个或上一个块"""
        line_idx = self.get_line_index(block_id)
        if line_idx == -1:
            return None
        
        target_idx = line_idx + 1 if direction == "next" else line_idx - 1
        if target_idx < 0 or target_idx >= len(self.blocks_list):
            return None
        
        block = self.blocks_list[target_idx]
        return {
            "id": block["id"],
            "block_type": block["block_type"],
            "language": block.get("language"),
            "content": block.get("content", "")[:500],
            "line_index": target_idx
        }
    
    def get_block_by_id(self, block_id: str) -> Optional[Dict]:
        """根据ID获取块"""
        block = self.blocks_dict.get(block_id)
        if not block:
            return None
        return {
            "id": block["id"],
            "block_type": block["block_type"],
            "language": block.get("language"),
            "content": block.get("content", ""),
            "line_index": self.get_line_index(block_id)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        code_blocks = [b for b in self.blocks_list if b["block_type"] == "code"]
        
        lang_stats = {}
        for b in code_blocks:
            lang = b.get("language", "unknown")
            lang_stats[lang] = lang_stats.get(lang, 0) + 1
        
        return {
            "total_blocks": len(self.blocks_list),
            "code_blocks": len(code_blocks),
            "markdown_blocks": len(self.blocks_list) - len(code_blocks),
            "languages": lang_stats,
            "cache_size": len(self.cache),
            "history_count": len(self.history)
        }
    def get_continuous_blocks(self, block_id: str, count: int = 5) -> List[Dict]:
        """
        获取从指定块开始的连续多个块
        
        Args:
            block_id: 起始块ID
            count: 连续块数量
        
        Returns:
            连续块列表
        """
        line_idx = self.get_line_index(block_id)
        if line_idx == -1:
            return []
        
        results = []
        end_idx = min(line_idx + count, len(self.blocks_list))
        
        for i in range(line_idx, end_idx):
            block = self.blocks_list[i]
            results.append({
                "id": block["id"],
                "block_type": block["block_type"],
                "language": block.get("language"),
                "content": block.get("content", ""),
                "line_index": i,
                "concept_hierarchy": block.get("concept_hierarchy", [])
            })
        
        return results    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取检索历史"""
        return self.history[-limit:]


# ============ 独立使用示例 ============
if __name__ == "__main__":
    # 测试代码
    api = OIRetrieverAPI()
    
    print("\n" + "="*60)
    print("API 测试")
    print("="*60)
    
    # 测试搜索
    result = api.search("线段树区间修改", top_k=2)
    print(f"\n查询: {result['query']}")
    print(f"耗时: {result['time_ms']}ms")
    for i, r in enumerate(result['results']):
        print(f"\n  [{i+1}] 得分: {r['score']:.4f}")
        print(f"       路径: {' → '.join(r['concept_hierarchy'])}")
    
    # 统计信息
    stats = api.get_stats()
    print(f"\n统计信息:")
    print(f"  总块数: {stats['total_blocks']}")
    print(f"  C++代码: {stats['languages'].get('cpp', 0)}")
    print(f"  Python代码: {stats['languages'].get('python', 0)}")