"""
OI-Wiki 检索器 Web 演示界面
使用 Gradio 构建
安装：pip install gradio
"""

import gradio as gr
from oi_retriever_api import OIRetrieverAPI
import time

# 初始化 API（全局变量，避免重复加载）
print("🚀 初始化 OI-Wiki 检索器...")
api = OIRetrieverAPI()
print("✅ 初始化完成！")

def format_result(result, show_content=True):
    """格式化单个结果为 HTML"""
    concept_path = " → ".join(result["concept_hierarchy"])
    score = result["score"]
    block_type = result["block_type"]
    language = result.get("language", "")
    lang_tag = f"[{language}]" if language else ""
    
    # 基础信息
    html = f"""
    <div style="border:1px solid #ddd; border-radius:8px; padding:12px; margin:10px 0; background-color:#f9f9f9;">
        <div style="display:flex; justify-content:space-between;">
            <span style="font-weight:bold; color:#2c3e50;">{concept_path}</span>
            <span style="color:#e67e22;">得分: {score:.4f}</span>
        </div>
        <div style="margin-top:8px; color:#7f8c8d;">
            <span>类型: {block_type} {lang_tag}</span>
            <span style="margin-left:20px;">行号: {result.get('line_index', 'N/A')}</span>
        </div>
    """
    
    # 内容预览
    if show_content and "content" in result:
        content = result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"]
        html += f"""
        <div style="margin-top:8px; padding:8px; background-color:#fff; border-radius:4px; font-family:monospace; white-space:pre-wrap; font-size:12px;">
            {content}
        </div>
        """
    
    # 上下文
    if "context" in result and result["context"]:
        html += "<div style='margin-top:8px;'><details><summary>📎 上下文 (点击展开)</summary>"
        for ctx in result["context"][:3]:
            rel = "⬆️ 前文" if ctx["relation"] == "prev" else "⬇️ 后文"
            html += f"""
            <div style="margin:5px 0; padding:5px; background-color:#eef2f3; border-radius:4px;">
                <span style="color:#34495e;">{rel} [{ctx['type']}]</span>
                <div style="font-size:11px;">{ctx['preview'][:100]}...</div>
            </div>
            """
        html += "</details></div>"
    
    html += "</div>"
    return html

def search_interface(query, top_k, mode, code_only, language, show_content):
    """Gradio 接口函数"""
    if not query.strip():
        return "请输入查询内容", ""
    
    start = time.time()
    
    # 调用 API
    result = api.search(
        query=query,
        top_k=int(top_k),
        mode=mode,
        code_only=code_only,
        language=language if language != "全部" else None
    )
    
    elapsed = (time.time() - start) * 1000
    
    # 格式化结果
    if not result["results"]:
        return f"❌ 未找到结果 (耗时: {elapsed:.0f}ms)", ""
    
    stats = f"✅ 找到 {result['total']} 个结果 | 耗时: {elapsed:.0f}ms | 模式: {mode}"
    
    # 生成 HTML
    html_output = f"<div style='font-family: Arial, sans-serif;'>{stats}<hr>"
    
    for r in result["results"]:
        concept_path = " → ".join(r["concept_hierarchy"])
        score = r["score"]
        block_type = r["block_type"]
        language = r.get("language", "")
        lang_tag = f"[{language}]" if language else ""
        block_id = r["id"]
        line_idx = r.get("line_index", "N/A")
        
        # 基础信息
        html = f"""
        <div style="border:1px solid #ddd; border-radius:8px; padding:12px; margin:10px 0; background-color:#f9f9f9;">
            <div style="display:flex; justify-content:space-between;">
                <span style="font-weight:bold; color:#2c3e50;">{concept_path}</span>
                <span style="color:#e67e22;">得分: {score:.4f}</span>
            </div>
            <div style="margin-top:8px; color:#7f8c8d;">
                <span>类型: {block_type} {lang_tag}</span>
                <span style="margin-left:20px;">行号: {line_idx}</span>
                <span style="margin-left:20px;">ID: {block_id}</span>
            </div>
        """
        
        # 内容预览
        if show_content and "content" in r:
            content = r["content"][:300] + "..." if len(r["content"]) > 300 else r["content"]
            html += f"""
            <div style="margin-top:8px; padding:8px; background-color:#fff; border-radius:4px; font-family:monospace; white-space:pre-wrap; font-size:12px;">
                {content}
            </div>
            """
        
        # 上下文
        if "context" in r and r["context"]:
            html += "<div style='margin-top:8px;'><details><summary>📎 上下文 (点击展开)</summary>"
            for ctx in r["context"][:3]:
                rel = "⬆️ 前文" if ctx["relation"] == "prev" else "⬇️ 后文"
                html += f"""
                <div style="margin:5px 0; padding:5px; background-color:#eef2f3; border-radius:4px;">
                    <span style="color:#34495e;">{rel} [{ctx['type']}]</span>
                    <div style="font-size:11px;">{ctx['preview'][:100]}...</div>
                </div>
                """
            html += "</details></div>"
        
        # 添加连续块提示
        html += f"""
        <div style="margin-top:8px; padding:8px; background-color:#e8f4f8; border-radius:4px; font-size:12px;">
            📌 在「连续块」标签页输入ID <code style="background-color:#fff; padding:2px 5px;">{block_id}</code> 查看连续5个块
        </div>
        
        </div>
        """
        
        html_output += html
    
    html_output += "</div>"
    
    return html_output, stats

def get_block_info(block_id):
    """根据ID获取块信息"""
    block = api.get_block_by_id(block_id)
    if not block:
        return "❌ 未找到该块"
    
    html = f"""
    <div style="border:1px solid #3498db; border-radius:8px; padding:15px;">
        <h4>块信息</h4>
        <p><b>ID:</b> {block['id']}</p>
        <p><b>类型:</b> {block['block_type']} | 语言: {block.get('language', 'N/A')}</p>
        <p><b>行号:</b> {block['line_index']}</p>
        <div style="background-color:#f0f0f0; padding:10px; border-radius:4px; font-family:monospace; white-space:pre-wrap;">
            {block['content'][:500]}{'...' if len(block['content']) > 500 else ''}
        </div>
    </div>
    """
    return html

def get_next_block(block_id, direction):
    """获取下一个/上一个块"""
    block = api.get_next_block(block_id, direction)
    if not block:
        return f"❌ 没有{direction}块了"
    
    html = f"""
    <div style="border:1px solid #27ae60; border-radius:8px; padding:15px;">
        <h4>{'⬆️ 上一个块' if direction=='prev' else '⬇️ 下一个块'}</h4>
        <p><b>类型:</b> {block['block_type']} | 语言: {block.get('language', 'N/A')}</p>
        <p><b>行号:</b> {block['line_index']}</p>
        <div style="background-color:#f0f0f0; padding:10px; border-radius:4px; font-family:monospace; white-space:pre-wrap;">
            {block['content'][:300]}{'...' if len(block['content']) > 300 else ''}
        </div>
    </div>
    """
    return html

def get_stats():
    """获取统计信息"""
    stats = api.get_stats()
    html = f"""
    <div style="border:1px solid #9b59b6; border-radius:8px; padding:15px;">
        <h4>📊 知识库统计</h4>
        <ul>
            <li><b>总块数:</b> {stats['total_blocks']}</li>
            <li><b>代码块:</b> {stats['code_blocks']}</li>
            <li><b>文本块:</b> {stats['markdown_blocks']}</li>
            <li><b>C++代码:</b> {stats['languages'].get('cpp', 0)}</li>
            <li><b>Python代码:</b> {stats['languages'].get('python', 0)}</li>
            <li><b>Java代码:</b> {stats['languages'].get('java', 0)}</li>
            <li><b>其他语言:</b> {sum(v for k,v in stats['languages'].items() if k not in ['cpp','python','java'])}</li>
        </ul>
    </div>
    """
    return html

# 创建 Gradio 界面
with gr.Blocks(title="OI-Wiki 智能检索器", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 📚 OI-Wiki 智能检索器
    
    基于向量检索 + BM25 混合检索的 OI-Wiki 知识库搜索系统。
    """)
    
    with gr.Tab("🔍 检索"):
        with gr.Row():
            with gr.Column(scale=3):
                query_input = gr.Textbox(
                    label="输入查询",
                    placeholder="例如：线段树区间修改、SPFA SLF优化、快速排序实现...",
                    lines=2
                )
            with gr.Column(scale=1):
                submit_btn = gr.Button("🚀 开始检索", variant="primary", size="lg")
        
        with gr.Row():
            with gr.Column():
                top_k = gr.Slider(1, 10, value=3, step=1, label="返回结果数")
                mode = gr.Radio(["standard", "with_context"], value="standard", label="检索模式")
            with gr.Column():
                code_only = gr.Checkbox(False, label="只显示代码块")
                language = gr.Dropdown(["全部", "cpp", "python", "java"], value="全部", label="编程语言")
                show_content = gr.Checkbox(True, label="显示内容预览")
        
        with gr.Row():
            stats_output = gr.Textbox(label="状态", interactive=False)
        
        output_html = gr.HTML(label="检索结果")
        
        # 绑定事件
        submit_btn.click(
            search_interface,
            inputs=[query_input, top_k, mode, code_only, language, show_content],
            outputs=[output_html, stats_output]
        )
        
        # 回车也能搜索
        query_input.submit(
            search_interface,
            inputs=[query_input, top_k, mode, code_only, language, show_content],
            outputs=[output_html, stats_output]
        )
    
    with gr.Tab("📖 块详情"):
        with gr.Row():
            block_id_input = gr.Textbox(label="输入块ID", placeholder="例如: blk_20260212_354ab169")
            get_block_btn = gr.Button("查看详情", variant="primary")
        block_output = gr.HTML()
        
        get_block_btn.click(get_block_info, inputs=[block_id_input], outputs=[block_output])
    
    with gr.Tab("⬆️⬇️ 相邻块"):
        with gr.Row():
            nav_block_id = gr.Textbox(label="当前块ID", placeholder="输入块ID")
            nav_direction = gr.Radio(["next", "prev"], value="next", label="方向")
            nav_btn = gr.Button("查看", variant="primary")
        nav_output = gr.HTML()
        
        nav_btn.click(get_next_block, inputs=[nav_block_id, nav_direction], outputs=[nav_output])
    with gr.Tab("📚 连续块"):
        with gr.Row():
            continuous_block_id = gr.Textbox(
                label="起始块ID", 
                placeholder="例如: blk_20260212_354ab169"
            )
            continuous_count = gr.Slider(1, 10, value=5, step=1, label="连续块数量")
            continuous_btn = gr.Button("查看连续块", variant="primary")
        
        continuous_output = gr.HTML(label="连续块内容")
        
        def get_continuous_blocks_ui(block_id, count):
            """获取连续块并格式化显示"""
            if not block_id.strip():
                return "请输入块ID"
            
            blocks = api.get_continuous_blocks(block_id, int(count))
            if not blocks:
                return "❌ 未找到块"
            
            html = f"<h3>从行 {blocks[0]['line_index']} 开始的 {len(blocks)} 个连续块</h3>"
            
            for i, block in enumerate(blocks):
                # 添加分隔线（除了第一个）
                if i > 0:
                    html += "<hr style='border-top: 2px dashed #ccc; margin: 15px 0;'>"
                
                concept = " → ".join(block["concept_hierarchy"][-2:])  # 只显示最后两级概念
                lang_tag = f"[{block['language']}]" if block.get("language") else ""
                
                html += f"""
                <div style="margin:10px 0; padding:12px; background-color:{'#f0f8ff' if block['block_type']=='code' else '#fff'}; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-weight:bold; color:#2c3e50;">块 {i+1} (行 {block['line_index']})</span>
                        <span style="color:#7f8c8d;">{block['block_type']} {lang_tag}</span>
                    </div>
                    <div style="font-size:12px; color:#34495e; margin:5px 0;">{concept}</div>
                    <div style="margin-top:8px; padding:8px; background-color:#fff; border-radius:4px; font-family:monospace; white-space:pre-wrap; font-size:12px; max-height:200px; overflow-y:auto;">
                        {block['content'][:500]}{'...' if len(block['content']) > 500 else ''}
                    </div>
                </div>
                """
            
            return html
        
        continuous_btn.click(
            get_continuous_blocks_ui,
            inputs=[continuous_block_id, continuous_count],
            outputs=[continuous_output]
        )    
    with gr.Tab("📊 统计信息"):
        stats_btn = gr.Button("刷新统计")
        stats_output = gr.HTML()
        stats_btn.click(get_stats, outputs=[stats_output])
        
        # 页面加载时自动显示统计
        demo.load(get_stats, outputs=[stats_output])
    
    gr.Markdown("""
    ---
    ### 📝 使用说明
    - **检索模式**：standard（仅结果）/ with_context（带上下文）
    - **只显示代码块**：过滤掉 markdown 文本块
    - **编程语言**：只显示指定语言的代码块
    - **块ID**：在检索结果中可以看到每个块的 ID
    """)

if __name__ == "__main__":
    # 启动服务
    demo.launch(
        server_name="127.0.0.1",  # 本地访问
        server_port=7860,          # 端口
        share=False,               # 是否生成公共链接
        debug=True
    )