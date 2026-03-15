import os
import re
from typing import List

def process_file(file_path: str) -> List[str]:
    """处理单个文件，返回文本块列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            return []

    filename = os.path.basename(file_path)
    
    # .py 或 .cpp 文件：整个文件为一块
    if file_path.endswith(('.py', '.cpp')):
        return [f"文件名：{filename}\n\n{content}"]
    
    # .md 文件：按标题分块
    elif file_path.endswith('.md'):
        return split_md_file(content, filename)
    
    return []

def split_md_file(content: str, filename: str) -> List[str]:
    """拆分markdown文件"""
    lines = content.strip().split('\n')
    chunks = []
    
    # 获取主题（第一句话）
    theme = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            # 获取第一句话
            match = re.match(r'^([^。！？.!?]+[。！？.!?])', stripped)
            theme = match.group(1).strip() if match else stripped.split()[0]
            break
    
    # 处理标题和内容
    stack = []  # 存储祖先标题
    current_content = []
    
    for line in lines:
        stripped = line.strip()
        
        # 判断标题级别
        if stripped.startswith('#'):
            # 如果不是第一个标题，保存前一个块
            if current_content:
                chunk = f"文件名：{filename}\n主题：{theme}\n" + \
                       '\n'.join(stack) + \
                       f"\n\n{''.join(current_content)}"
                chunks.append(chunk)
                current_content = []
            
            # 计算标题级别
            match = re.match(r'^(#+)\s+(.+)$', stripped)
            if not match:
                continue
                
            level = len(match.group(1))
            title = match.group(2).strip()
            
            # 更新标题栈
            stack = stack[:level-1]
            stack.append(f"{'#'*level} {title}")
            
        elif stripped or current_content:
            # 收集非空内容
            current_content.append(line + '\n')
    
    # 添加最后一个块
    if current_content:
        chunk = f"文件名：{filename}\n主题：{theme}\n" + \
               '\n'.join(stack) + \
               f"\n\n{''.join(current_content)}"
        chunks.append(chunk)
    
    return chunks

def process_folder(root_dir: str) -> List[str]:
    """处理文件夹中的所有文件"""
    all_chunks = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(('.cpp', '.md', '.py')):
                file_path = os.path.join(root, file)
                chunks = process_file(file_path)
                all_chunks.extend(chunks)
    
    return all_chunks

# 使用示例
if __name__ == "__main__":
    chunks = process_folder("docs")
    
    print(f"总共处理了 {len(chunks)} 个文本块\n")
    
    # 显示前几个块作为示例
    for i, chunk in enumerate(chunks[:10]):
        print(f"=== 块 {i+1} ===")
        print(chunk[:300] + "..." if len(chunk) > 300 else chunk)