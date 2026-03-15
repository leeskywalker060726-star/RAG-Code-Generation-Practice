from google import genai
import os
import json
import re
from dotenv import load_dotenv
from analyzer import CodeAnalyzer
from retriever import KnowledgeRetriever
import time

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class RAGCompletionGenerator:
    def __init__(self):
        print("🚀 初始化 RAG 代码补全系统...")
        self.analyzer = CodeAnalyzer()
        self.retriever = KnowledgeRetriever()
        print("✅ 系统就绪")
    
    def generate_completion(self, code: str, cursor_pos: int) -> dict:
        start_time = time.time()
        
        # 1. 分析代码上下文
        print("🔍 [T5.1] 分析代码上下文...")
        analysis = self.analyzer.analyze_context(code, cursor_pos)
        
        # 2. 检索相关知识
        print(f"📚 [T5.2] 检索知识 (意图: {analysis.get('intent')})...")
        knowledge = self.retriever.retrieve_for_completion(analysis)
        
        # 3. 构建增强提示
        print("✨ [T5.3] 生成补全...")
        prompt = self._build_rag_prompt(analysis, knowledge, code)
        
        # 4. 调用 Gemini 生成
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        # 5. 解析补全建议
        completions = self._parse_completions(response.text)
        
        elapsed = time.time() - start_time
        
        return {
            "success": True,
            "analysis": analysis,
            "knowledge": knowledge,
            "completions": completions,
            "raw_response": response.text,
            "time_ms": int(elapsed * 1000)
        }
    
    def _build_rag_prompt(self, analysis: dict, knowledge: dict, original_code: str) -> str:
        code_examples = ""
        for i, ex in enumerate(knowledge["code_examples"][:3]):
            path = " → ".join(ex["concept_hierarchy"])
            lang = ex.get('language', 'cpp')
            code_examples += f"""
### 示例 {i+1} (来源: {path})
```{lang}
{ex['content'][:600]}
```
"""
        
        docs = ""
        for i, doc in enumerate(knowledge["explanations"][:2]):
            path = " → ".join(doc["concept_hierarchy"])
            docs += f"""
### 文档 {i+1} (来源: {path})
{doc['content'][:400]}
"""
        
        patterns = "\n".join([f"- {p.get('type')}: {p.get('name', p.get('description', ''))}" 
                             for p in knowledge["patterns"]])
        
        before = analysis["context_before"]
        after = analysis["context_after"]
        code_with_cursor = before + "<CURSOR>" + after
        
        prompt = f"""你是一个智能代码补全助手。基于以下信息，为光标位置(<CURSOR>)生成补全建议。

## 当前代码
```
{code_with_cursor[:1500]}
```

## 分析结果
- 语言: {analysis.get('language', 'cpp')}
- 意图: {analysis.get('intent', '未知')}
- 缺失: {analysis.get('missing_part', '未知')}

## 相关知识
{code_examples}
{docs}
{patterns}

## 任务
生成 3-5 个合理的补全建议，以 JSON 数组格式返回：
[
    {{
        "completion": "要补全的代码",
        "description": "说明",
        "source": "参考来源",
        "confidence": 0.0-1.0,
        "type": "function/loop/condition/expression"
    }}
]
"""
        return prompt
    
    def _parse_completions(self, response_text: str) -> list:
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return [{
            "completion": response_text[:300],
            "description": "生成的补全",
            "source": "模型生成",
            "confidence": 0.5,
            "type": "code"
        }]