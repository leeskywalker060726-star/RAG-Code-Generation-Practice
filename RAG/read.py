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
    if file_path.endswith(('.py', '.cpp')):
        return [f"文件名：{filename}\n\n{content}"]
    elif file_path.endswith('.md'):
        return split_md_file(content, filename)
    return []
def split_md_file(content: str, filename: str) -> List[str]:
    """拆分markdown文件"""
    lines = content.strip().split('\n')
    chunks = []
    theme = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            match = re.match(r'^([^。！？.!?]+[。！？.!?])', stripped)
            theme = match.group(1).strip() if match else stripped.split()[0]
            break
    stack = [] 
    current_content = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            if current_content:
                chunk = f"文件名：{filename}\n主题：{theme}\n" + \
                       '\n'.join(stack) + \
                       f"\n\n{''.join(current_content)}"
                chunks.append(chunk)
                current_content = []
            match = re.match(r'^(#+)\s+(.+)$', stripped)
            if not match:
                continue
            level = len(match.group(1))
            title = match.group(2).strip()
            stack = stack[:level-1]
            stack.append(f"{'#'*level} {title}")
        elif stripped or current_content:
            current_content.append(line + '\n')
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

if __name__ == "__main__":
    chunks = process_folder("docs")
    print(f"总共处理了 {len(chunks)} 个文本块\n")
    for i, chunk in enumerate(chunks[:10]):
        print(f"=== 块 {i+1} ===")
        print(chunk[:300] + "..." if len(chunk) > 300 else chunk)