from flask import Flask, render_template_string, request, jsonify
from oi_retriever_api import OIRetrieverAPI
import time

# 初始化 Flask 应用
app = Flask(__name__)

# 初始化 API（全局变量，避免重复加载）
print("🚀 初始化 OI-Wiki 检索器...")
api = OIRetrieverAPI()
print("✅ 初始化完成！")

# ====================== 工具函数（完全保留原逻辑） ======================
def format_result(result, show_content=True):
    """格式化单个结果为 HTML"""
    concept_path = " → ".join(result["concept_hierarchy"])
    score = result["score"]
    block_type = result["block_type"]
    language = result.get("language", "")
    lang_tag = f"[{language}]" if language else ""
    
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
    
    if show_content and "content" in result:
        content = result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"]
        html += f"""
        <div style="margin-top:8px; padding:8px; background-color:#fff; border-radius:4px; font-family:monospace; white-space:pre-wrap; font-size:12px;">
            {content}
        </div>
        """
    
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

# ====================== 核心业务函数（完全保留） ======================
def search_interface(query, top_k, mode, code_only, language, show_content):
    if not query.strip():
        return "请输入查询内容", ""
    
    start = time.time()
    
    result = api.search(
        query=query,
        top_k=int(top_k),
        mode=mode,
        code_only=code_only,
        language=language if language != "全部" else None
    )
    
    elapsed = (time.time() - start) * 1000
    
    if not result["results"]:
        return f"❌ 未找到结果 (耗时: {elapsed:.0f}ms)", ""
    
    stats = f"✅ 找到 {result['total']} 个结果 | 耗时: {elapsed:.0f}ms | 模式: {mode}"
    html_output = f"<div style='font-family: Arial, sans-serif;'>{stats}<hr>"
    
    for r in result["results"]:
        concept_path = " → ".join(r["concept_hierarchy"])
        score = r["score"]
        block_type = r["block_type"]
        language = r.get("language", "")
        lang_tag = f"[{language}]" if language else ""
        block_id = r["id"]
        line_idx = r.get("line_index", "N/A")
        
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
        
        if show_content and "content" in r:
            content = r["content"][:300] + "..." if len(r["content"]) > 300 else r["content"]
            html += f"""
            <div style="margin-top:8px; padding:8px; background-color:#fff; border-radius:4px; font-family:monospace; white-space:pre-wrap; font-size:12px;">
                {content}
            </div>
            """
        
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

def get_continuous_blocks_ui(block_id, count):
    if not block_id.strip():
        return "请输入块ID"
    
    blocks = api.get_continuous_blocks(block_id, int(count))
    if not blocks:
        return "❌ 未找到块"
    
    html = f"<h3>从行 {blocks[0]['line_index']} 开始的 {len(blocks)} 个连续块</h3>"
    for i, block in enumerate(blocks):
        if i > 0:
            html += "<hr style='border-top: 2px dashed #ccc; margin: 15px 0;'>"
        
        concept = " → ".join(block["concept_hierarchy"][-2:])
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

# ====================== Flask 网页模板（复刻 Gradio 界面） ======================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>oi-wiki向量化质量与血源性分析检索器</title>
    <style>
        * {box-sizing: border-box; font-family: Arial, sans-serif;}
        body {max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5;}
        .tab {overflow: hidden; border: 1px solid #ccc; background: #fff; border-radius: 8px 8px 0 0;}
        .tab button {background: inherit; border: none; outline: none; cursor: pointer; padding: 14px 16px; transition: 0.3s; font-size: 16px;}
        .tab button:hover {background: #ddd;}
        .tab button.active {background: #007bff; color: black;}
        .tabcontent {display: none; padding: 20px; border: 1px solid #ccc; border-top: none; background: white; border-radius: 0 0 8px 8px;}
        .row {display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap;}
        .col {flex: 1; min-width: 250px;}
        input, select, textarea, button {width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;}
        button {background: #007bff; color: black; border: none; cursor: pointer; font-weight: bold;}
        button:hover {opacity: 0.9;}
        .result {margin-top: 15px; padding: 10px;}
    </style>
</head>
<body>
    <h1>oi-wiki向量化质量与血源性分析检索器</h1>
    <p>基于向量检索 + BM25 混合检索的 OI-Wiki 知识库搜索系统。</p>

    <div class="tab">
        <button class="tablinks active" onclick="openTab(event, 'search')">🔍 检索</button>
        <button class="tablinks" onclick="openTab(event, 'block')">📖 块详情</button>
        <button class="tablinks" onclick="openTab(event, 'nav')">⬆️⬇️ 相邻块</button>
        <button class="tablinks" onclick="openTab(event, 'continuous')">📚 连续块</button>
        <button class="tablinks" onclick="openTab(event, 'stats')">📊 统计信息</button>
    </div>

    <!-- 检索标签页 -->
    <div id="search" class="tabcontent" style="display:block;">
        <div class="row">
            <div class="col" style="flex:3;">
                <textarea id="query" placeholder="例如：线段树区间修改、SPFA SLF优化、快速排序实现..." rows="2"></textarea>
            </div>
            <div class="col" style="flex:1;">
                <button onclick="search()">🚀 开始检索</button>
            </div>
        </div>
        <div class="row">
            <div class="col">
                <label>返回结果数</label>
                <input type="range" id="top_k" min="1" max="10" value="3" step="1">
                <label>检索模式</label>
                <select id="mode">
                    <option value="standard">standard</option>
                    <option value="with_context">with_context</option>
                </select>
            </div>
            <div class="col">
                <label><input type="checkbox" id="code_only"> 只显示代码块</label>
                <label>编程语言</label>
                <select id="language">
                    <option>全部</option>
                    <option>cpp</option>
                    <option>python</option>
                    <option>java</option>
                </select>
                <label><input type="checkbox" id="show_content" checked> 显示内容预览</label>
            </div>
        </div>
        <div class="result">
            <input type="text" id="stats_output" readonly placeholder="状态">
            <div id="output_html"></div>
        </div>
    </div>

    <!-- 块详情 -->
    <div id="block" class="tabcontent">
        <div class="row">
            <input type="text" id="block_id" placeholder="例如: blk_20260212_354ab169">
            <button onclick="getBlock()">查看详情</button>
        </div>
        <div id="block_output" class="result"></div>
    </div>

    <!-- 相邻块 -->
    <div id="nav" class="tabcontent">
        <div class="row">
            <input type="text" id="nav_block_id" placeholder="输入块ID">
            <select id="nav_direction">
                <option value="next">next</option>
                <option value="prev">prev</option>
            </select>
            <button onclick="getNav()">查看</button>
        </div>
        <div id="nav_output" class="result"></div>
    </div>

    <!-- 连续块 -->
    <div id="continuous" class="tabcontent">
        <div class="row">
            <input type="text" id="continuous_block_id" placeholder="例如: blk_20260212_354ab169">
            <input type="range" id="continuous_count" min="1" max="10" value="5" step="1">
            <button onclick="getContinuous()">查看连续块</button>
        </div>
        <div id="continuous_output" class="result"></div>
    </div>

    <!-- 统计 -->
    <div id="stats" class="tabcontent">
        <button onclick="getStats()">刷新统计</button>
        <div id="stats_output_html" class="result"></div>
    </div>

    <hr>
    <h3>📝 使用说明</h3>
    <ul>
        <li>检索模式：standard（仅结果）/ with_context（带上下文）</li>
        <li>只显示代码块：过滤掉 markdown 文本块</li>
        <li>编程语言：只显示指定语言的代码块</li>
        <li>块ID：在检索结果中可以看到每个块的 ID</li>
    </ul>

    <script>
        // 标签页切换
        function openTab(evt, tabName) {
            let i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) tabcontent[i].style.display = "none";
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) tablinks[i].className = tablinks[i].className.replace(" active", "");
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }

        // 检索
        async function search() {
            let res = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    query: document.getElementById('query').value,
                    top_k: document.getElementById('top_k').value,
                    mode: document.getElementById('mode').value,
                    code_only: document.getElementById('code_only').checked,
                    language: document.getElementById('language').value,
                    show_content: document.getElementById('show_content').checked
                })
            });
            let data = await res.json();
            document.getElementById('output_html').innerHTML = data.html;
            document.getElementById('stats_output').value = data.stats;
        }

        // 块详情
        async function getBlock() {
            let res = await fetch('/api/block', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({block_id: document.getElementById('block_id').value})
            });
            document.getElementById('block_output').innerHTML = await res.text();
        }

        // 相邻块
        async function getNav() {
            let res = await fetch('/api/nav', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    block_id: document.getElementById('nav_block_id').value,
                    direction: document.getElementById('nav_direction').value
                })
            });
            document.getElementById('nav_output').innerHTML = await res.text();
        }

        // 连续块
        async function getContinuous() {
            let res = await fetch('/api/continuous', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    block_id: document.getElementById('continuous_block_id').value,
                    count: document.getElementById('continuous_count').value
                })
            });
            document.getElementById('continuous_output').innerHTML = await res.text();
        }

        // 统计
        async function getStats() {
            let res = await fetch('/api/stats');
            document.getElementById('stats_output_html').innerHTML = await res.text();
        }

        // 回车搜索
        document.getElementById('query').addEventListener('keypress', e => {
            if (e.key === 'Enter') search();
        });

        // 页面加载统计
        window.onload = getStats;
    </script>
</body>
</html>
"""

# ====================== Flask 路由 ======================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    html, stats = search_interface(
        data['query'], data['top_k'], data['mode'],
        data['code_only'], data['language'], data['show_content']
    )
    return jsonify({'html': html, 'stats': stats})

@app.route('/api/block', methods=['POST'])
def api_block():
    return get_block_info(request.json['block_id'])

@app.route('/api/nav', methods=['POST'])
def api_nav():
    data = request.json
    return get_next_block(data['block_id'], data['direction'])

@app.route('/api/continuous', methods=['POST'])
def api_continuous():
    data = request.json
    return get_continuous_blocks_ui(data['block_id'], data['count'])

@app.route('/api/stats')
def api_stats():
    return get_stats()

# ====================== 启动服务 ======================
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=7860,
        debug=True
    )