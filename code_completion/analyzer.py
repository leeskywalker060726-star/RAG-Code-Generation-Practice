from google import genai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# 初始化 Gemini 客户端
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class CodeAnalyzer:
    def analyze_context(self, code: str, cursor_pos: int) -> dict:
        """
        让 LLM 分析代码上下文，判断需要补全什么
        """
        # 分割代码
        before = code[:cursor_pos]
        after = code[cursor_pos:]
        
        # 提取最后几行作为上下文
        lines_before = before.split('\n')
        recent_context = '\n'.join(lines_before[-15:]) if lines_before else ""
        
        prompt = f"""你是一个代码补全专家。分析以下代码，判断光标位置需要补全什么。

代码（光标前）：
```
{recent_context}
```

代码（光标后）：
```
{after[:200]}
```

请分析：
1. 这是什么编程语言？
2. 光标处最可能缺少什么？
3. 如果要搜索相关知识库，应该用什么关键词？

以 JSON 格式返回：
{{
    "language": "检测到的语言 (cpp/python/java)",
    "intent": "补全意图（一句话描述）",
    "missing_part": "缺失部分详细描述",
    "search_query": "用于检索的完整查询"
}}
"""
        
        try:
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt
            )
            
            # 解析 JSON
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = self._fallback_analysis(before, after)
        except Exception as e:
            print(f"⚠️ 分析失败: {e}")
            result = self._fallback_analysis(before, after)
        
        result["context_before"] = before
        result["context_after"] = after
        result["cursor_pos"] = cursor_pos
        return result
    
    def _fallback_analysis(self, before: str, after: str) -> dict:
        last_line = before.split('\n')[-1] if before else ""
        
        language = "cpp"
        if "def " in before or "import " in before:
            language = "python"
        elif "public class" in before or "System.out" in before:
            language = "java"
        
        intent = "代码补全"
        if last_line.strip().endswith(":"):
            if "def " in last_line:
                intent = "函数体补全"
            elif "class " in last_line:
                intent = "类定义补全"
            elif "for " in last_line or "while " in last_line:
                intent = "循环体补全"
            elif "if " in last_line:
                intent = "条件分支补全"
        
        words = re.findall(r'\b(\w+)$', last_line)
        keyword = words[-1] if words else "code"
        
        return {
            "language": language,
            "intent": intent,
            "missing_part": f"需要补全{intent}",
            "search_query": f"{language} {intent} {keyword}"
        }