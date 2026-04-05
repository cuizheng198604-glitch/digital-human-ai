# -*- coding: utf-8 -*-
"""
数字人AI - 公网访问辅助工具
使用方法: python public_link.py
"""
import os
import sys
import time
import subprocess
import socket
import webbrowser

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

def start_flask():
    """启动Flask服务器"""
    print("正在启动Flask服务器...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if not check_port(5000):
        print("端口5000已被占用，跳过启动")
        return False
    
    # 在后台启动
    subprocess.Popen(
        [sys.executable, 'web/app.py'],
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    time.sleep(2)
    print("Flask服务器已启动")
    return True

def try_tunnel_service(service_name, cmd):
    """尝试隧道服务"""
    print(f"尝试 {service_name}...")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        url = None
        for line in iter(proc.stdout.readline, ''):
            if line:
                print(f"  {line.strip()}")
                # 提取URL
                if 'https://' in line or 'http://' in line:
                    for word in line.split():
                        if 'https://' in word or (word.startswith('http') and '.ngrok' in word):
                            url = word.strip()
                            break
                # serveo
                if 'serveo.net' in line and ('http' in line or 'https' in line):
                            url = line.split('https://')[-1].split()[0] if 'https://' in line else line.split('http://')[-1].split()[0]
                            url = 'https://' + url
                # localhost.run
                if 'localhost.run' in line or 'sshlocalhost' in line:
                    parts = line.split()
                    for p in parts:
                        if p.startswith('http') and 'localhost' in p:
                            url = p
                            break
                            
            # 检查是否还在运行
            if proc.poll() is not None:
                break
                
        return proc, url
    except Exception as e:
        print(f"  失败: {e}")
        return None, None

def main():
    print("=" * 50)
    print("  数字人 AI - 公网链接生成器")
    print("=" * 50)
    print()
    
    # 1. 启动Flask
    start_flask()
    
    # 2. 显示本地地址
    local_ip = get_local_ip()
    print()
    print(f"本地访问: http://localhost:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    print()
    
    # 3. 尝试各种隧道服务
    print("=" * 50)
    print("  正在创建公网链接...")
    print("=" * 50)
    print()
    
    # 尝试顺序: serveo -> localhost.run -> ngtrok
    tunnels = [
        ("serveo.net", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", 
                        "-R", "80:localhost:5000", "serveo.net"]),
        ("localhost.run", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60",
                          "-R", "80:localhost:5000", "ssh.localhost.run"]),
    ]
    
    url = None
    proc = None
    
    for name, cmd in tunnels:
        proc, url = try_tunnel_service(name, cmd)
        if url:
            break
        time.sleep(1)
    
    print()
    if url:
        print("=" * 50)
        print("  ✅ 公网链接创建成功!")
        print("=" * 50)
        print()
        print(f"公网访问地址:")
        print(f"  {url}")
        print()
        print("把这个链接发给朋友，他们可以直接答题！")
        print()
        print("提示: 关闭此窗口会断开链接")
        
        # 打开浏览器
        webbrowser.open(url)
    else:
        print("=" * 50)
        print("  ⚠️  自动隧道失败")
        print("=" * 50)
        print()
        print("请手动尝试以下方法:")
        print()
        print("方法1 - 使用ngrok (推荐):")
        print("  1. 访问 https://ngrok.com 下载并注册")
        print("  2. 解压后运行: ngrok http 5000")
        print("  3. 把显示的 https://xxx.ngrok.io 链接发给别人")
        print()
        print("方法2 - 使用Cloudflare Tunnel:")
        print("  1. 下载 cloudflared")
        print("  2. 运行: cloudflared tunnel --url http://localhost:5000")
        print()
        print("方法3 - 蒲公英内网通:")
        print("  1. 访问 https://pgy.top 注册")
        print("  2. 下载客户端软件")
        print("  3. 创建隧道指向 localhost:5000")
    
    print()
    input("按回车键退出...")
    if proc:
        proc.terminate()

if __name__ == '__main__':
    main()
