import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List

# 加载环境变量
load_dotenv()

# 配置Google AI
api_key = os.getenv("GOOGLE_API_KEY")
#if not api_key:
#    raise ValueError("请设置GOOGLE_API_KEY环境变量")

genai.configure(api_key=api_key)

def generate(query: str, chunks: List[str]) -> str:
    """使用Gemini生成答案"""
    
    # 构建提示词
    context = "\n\n".join(chunks[:5])  # 只使用前5个相关片段，避免太长
    prompt = f"""你是一个智能开发助手，专门帮助解决算法和编程问题。

用户问题: {query}

相关参考内容:
{context}

请基于上述参考内容，给出准确、简洁的回答。如果参考内容中没有相关信息，请说明无法回答。

回答要求:
1. 如果有代码示例，请提供完整可运行的代码
2. 解释算法的核心思想
3. 分析时间和空间复杂度
4. 提供使用示例

回答:"""
    
    try:
        # 创建模型实例
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 生成回答
        response = model.generate_content(prompt)
        
        # 返回回答文本
        return response.text
        
    except Exception as e:
        return f"生成回答时出错: {str(e)}"

# 使用示例
if __name__ == "__main__":
    # 测试数据
    test_query = "如何实现快速排序？"
    test_chunks = [
        "快速排序是一种分治算法，平均时间复杂度为O(n log n)",
        "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)",
        "快速排序在最坏情况下时间复杂度为O(n²)，但通过随机选择枢轴可以避免"
    ]
    
    answer = generate(test_query, test_chunks)
    print("问题:", test_query)
    print("\n回答:")
    print(answer)