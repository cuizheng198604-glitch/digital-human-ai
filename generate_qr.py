# -*- coding: utf-8 -*-
"""
生成二维码图片用于分享
"""
import urllib.request
import os

def generate_qr(url, output_path):
    """生成二维码"""
    api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(url)}"
    
    try:
        response = urllib.request.urlopen(api_url)
        with open(output_path, 'wb') as f:
            f.write(response.read())
        print(f"二维码已生成: {output_path}")
        return output_path
    except Exception as e:
        print(f"生成失败: {e}")
        return None

if __name__ == '__main__':
    import urllib.parse
    
    # 配置
    local_ip = "192.168.3.128"  # 替换为实际IP
    port = 5000
    share_url = f"http://{local_ip}:{port}/share"
    
    output = os.path.join(os.path.dirname(__file__), 'data', 'share_qr.png')
    os.makedirs(os.path.dirname(output), exist_ok=True)
    
    generate_qr(share_url, output)
