import socket
import subprocess
import sys

def check_port(port):
    """检查单个端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result != 0  # 0表示端口被占用
    except:
        return False

def find_available_ports(start_port=7860, end_port=7900):
    """查找可用端口范围"""
    available = []
    for port in range(start_port, end_port + 1):
        if check_port(port):
            available.append(port)
    return available

def kill_process_on_port(port):
    """杀死占用端口的进程"""
    try:
        # Windows 系统
        if sys.platform == 'win32':
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[4]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                        print(f"✅ 已杀死进程 PID: {pid}")
        else:
            # Linux/Mac
            subprocess.run(f'lsof -ti:{port} | xargs kill -9', shell=True)
            print(f"✅ 已杀死占用端口 {port} 的进程")
        return True
    except Exception as e:
        print(f"❌ 杀死进程失败: {e}")
        return False

def main():
    print("🔍 端口可用性检查工具")
    print("=" * 50)
    
    # 检查常用端口
    common_ports = [7860, 7861, 7862, 7863, 7864, 7865, 7866, 7867, 7868, 7869, 7870]
    
    print("\n📊 常用端口状态：")
    for port in common_ports:
        status = "✅ 可用" if check_port(port) else "❌ 被占用"
        print(f"  端口 {port}: {status}")
    
    # 查找可用端口
    available = find_available_ports(7860, 7900)
    
    print(f"\n📌 可用端口列表: {available}")
    
    if available:
        print(f"\n✨ 推荐使用端口: {available[0]}")
        print(f"\n在 app.py 中修改:")
        print(f"   port = {available[0]}")
    else:
        print("\n⚠️ 没有找到可用端口，尝试释放被占用的端口...")
        
        # 尝试释放最常用的几个端口
        for port in [7860, 7861, 7862, 7863, 7864, 7865]:
            if not check_port(port):
                print(f"\n🔄 尝试释放端口 {port}...")
                if kill_process_on_port(port):
                    if check_port(port):
                        print(f"✅ 端口 {port} 现已可用")
                        break
    
    # 显示当前所有Python进程
    print("\n📋 当前运行的 Python 进程：")
    if sys.platform == 'win32':
        result = subprocess.run(
            'tasklist | findstr python',
            shell=True, capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            'ps aux | grep python',
            shell=True, capture_output=True, text=True
        )
    
    if result.stdout:
        print(result.stdout)
    else:
        print("   没有找到 Python 进程")
    
    print("\n💡 提示：")
    print("   - 如果端口被占用，可以手动结束进程")
    print("   - 或者修改 app.py 中的端口号")
    print("   - 在 app.py 中设置 port = 可用端口")

if __name__ == "__main__":
    main()