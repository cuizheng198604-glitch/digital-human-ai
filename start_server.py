# -*- coding: utf-8 -*-
"""
Digital Human AI - 服务器启动器
支持本地访问和公网隧道
"""
import os
import sys
import webbrowser
import socket
import subprocess
import time

def get_local_ip():
    """获取局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def check_port(port):
    """检查端口是否被占用"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', port))
        s.close()
        return True
    except:
        return False

def main():
    port = 5000
    
    print("=" * 50)
    print("  数字人 AI - 问卷系统")
    print("=" * 50)
    print()
    
    # 检查端口
    if not check_port(port):
        print(f"[!] 端口 {port} 已被占用，尝试关闭旧进程...")
        try:
            subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True)
        except:
            pass
    
    # 显示访问地址
    local_ip = get_local_ip()
    
    print(f"本地访问地址:")
    print(f"  http://localhost:{port}")
    print(f"  http://{local_ip}:{port}")
    print()
    print("移动端/其他设备访问:")
    print(f"  http://{local_ip}:{port}")
    print()
    print("分享页面:")
    print(f"  http://{local_ip}:{port}/share")
    print()
    
    # 启动浏览器
    print("正在启动 Flask 服务器...")
    webbrowser.open(f'http://localhost:{port}')
    
    # 启动 Flask
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    from web.app import app
    
    print()
    print("=" * 50)
    print("  服务器已启动！")
    print("=" * 50)
    print()
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n服务器已停止")

if __name__ == '__main__':
    main()
