@echo off
chcp 65001 >nul
title 数字人AI - 公网链接生成器

echo ================================================
echo   数字人 AI - 生成公网访问链接
echo ================================================
echo.
echo 正在启动本地服务器 (如果未启动)...
echo.

:: 启动 Flask (如果没运行)
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    start "Flask Server" cmd /k "cd /d %~dp0 && py web/app.py"
    echo 等待服务器启动...
    timeout /t 3 /nobreak >nul
)

echo.
echo 正在创建公网链接 (使用 serveo.net)...
echo 此链接可以发给任何人，无需安装任何软件
echo.
echo ================================================
echo.

:: 使用 SSH 创建隧道到 serveo.net
start "公网链接" cmd /k "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:localhost:5000 serveo.net"

echo.
echo 等待连接建立...
timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo   公网访问说明
echo ================================================
echo.
echo 1. 查看上方 "公网链接" 窗口
echo 2. 等待显示类似: "Forwarding HTTP traffic from https://xxxx.serveo.net"
echo 3. 那个 HTTPS 链接就是你的公网地址
echo 4. 把链接发给朋友，他们就能答题了
echo.
echo 注意事项:
echo - 链接有效期直到关闭此窗口
echo - 需要保持网络畅通
echo - 如果连接失败，尝试刷新重试
echo.
pause
