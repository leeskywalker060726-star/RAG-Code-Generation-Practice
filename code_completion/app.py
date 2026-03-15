import os
import ssl

# 禁用 SSL 验证（临时解决）
os.environ['CURL_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context
from flask import Flask, request, jsonify, render_template
from generator import RAGCompletionGenerator
import time

# 初始化生成器
print("🚀 启动 RAG 代码补全系统...")
generator = RAGCompletionGenerator()
print("✅ 系统启动完成")

app = Flask(__name__)

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/complete', methods=['POST'])
def complete():
    """代码补全 API"""
    try:
        data = request.json
        code = data.get('code', '')
        cursor_pos = data.get('cursor_pos', len(code))
        
        if not code:
            return jsonify({'error': '请输入代码'}), 400
        
        # 调用生成器
        result = generator.generate_completion(code, int(cursor_pos))
        
        # 格式化返回
        return jsonify({
            'success': True,
            'completions': result['completions'],
            'analysis': result['analysis'],
            'knowledge': {
                'code_count': len(result['knowledge']['code_examples']),
                'doc_count': len(result['knowledge']['explanations'])
            },
            'time_ms': result['time_ms']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        threaded=True
    )