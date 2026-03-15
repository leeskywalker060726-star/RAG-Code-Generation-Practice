import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oi_retriever_api import OIRetrieverAPI
import re

class KnowledgeRetriever:
    def __init__(self):
        print("📚 初始化知识检索器...")
        self.api = OIRetrieverAPI()
        print("✅ 检索器就绪")
    
    def retrieve_for_completion(self, analysis: dict, top_k: int = 5) -> dict:
        language = analysis.get("language", "cpp")
        intent = analysis.get("intent", "")
        search_query = analysis.get("search_query", "")
        
        # 构建多个检索查询
        queries = [
            f"{language} {intent} {search_query}",
            f"{language} {intent}",
            f"{language} 代码示例"
        ]
        
        all_code_results = []
        all_doc_results = []
        
        for q in queries:
            if not q.strip():
                continue
            
            # 检索代码
            code_results = self.api.search(
                query=q,
                top_k=top_k,
                code_only=True,
                language=language
            )
            all_code_results.extend(code_results["results"])
            
            # 检索文档
            doc_results = self.api.search(
                query=q + " 原理",
                top_k=2,
                code_only=False
            )
            all_doc_results.extend(doc_results["results"])
        
        # 去重
        code_examples = self._deduplicate(all_code_results)[:top_k]
        explanations = self._deduplicate(all_doc_results)[:3]
        
        # 提取代码模式
        patterns = self._extract_patterns(code_examples)
        
        return {
            "code_examples": code_examples,
            "explanations": explanations,
            "patterns": patterns,
            "search_details": {
                "queries": queries,
                "total_code": len(code_examples),
                "total_doc": len(explanations)
            }
        }
    
    def _deduplicate(self, items: list) -> list:
        seen = set()
        unique = []
        for item in items:
            content_hash = hash(item.get("content", "")[:200])
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(item)
        return unique
    
    def _extract_patterns(self, code_blocks: list) -> list:
        patterns = []
        for block in code_blocks[:3]:
            code = block.get("content", "")
            funcs = re.findall(r'(def|void|int|bool|char)\s+(\w+)\s*\([^)]*\)', code)
            for f in funcs:
                patterns.append({
                    "type": "function",
                    "name": f[1],
                    "signature": f[0] + " " + f[1] + "(...)"
                })
            if re.search(r'for\s*\(|while\s*\(', code):
                patterns.append({"type": "loop", "description": "循环结构"})
            if re.search(r'if\s*\(|else', code):
                patterns.append({"type": "condition", "description": "条件分支"})
        return patterns