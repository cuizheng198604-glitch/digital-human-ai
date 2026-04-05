# -*- coding: utf-8 -*-
import os
import sys
import threading
import time

# 启动Flask服务器
def run_flask():
    os.chdir(r'C:\Users\Administrator\Projects\digital_human_ai')
    from web.app import app
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)

# 启动Flask线程
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

print("Flask服务器已启动在 http://0.0.0.0:5000")
print("按 Ctrl+C 停止")

# 保持运行
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n服务器已停止")
