@echo off
chcp 65001 >nul
title 数字人AI - 启动器

echo ================================================
echo   数字人 AI - 问卷系统启动器
echo ================================================
echo.
echo [1] 仅启动本地服务器 (局域网访问)
echo [2] 启动 + 生成公网链接 (ngrok)
echo [3] 查看当前访问地址
echo [4] 退出
echo.

set /p choice=请选择 (1-4):

if "%choice%"=="1" goto local
if "%choice%"=="2" goto tunnel
if "%choice%"=="3" goto info
if "%choice%"=="4" goto end

:local
echo.
echo 正在启动本地服务器...
cd /d "%~dp0"
py web/app.py
goto end

:tunnel
echo.
echo 检查 ngrok...
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo ngrok 未安装，正在下载...
    powershell -Command "Invoke-WebRequest -Uri 'https://bin.equinox.io/c/4VmDzA7iaH/ngrok-stable-windows-amd64.zip' -OutFile 'ngrok.zip'"
    powershell -Command "Expand-Archive -Path 'ngrok.zip' -DestinationPath '.' -Force"
    del ngrok.zip
    echo.
    echo 请到 https://dashboard.ngrok.com/signup 注册并获取 Authtoken
    echo 然后运行: ngrok config add-authtoken <your-token>
    echo.
    set /p token=请输入 ngrok token:
    ngrok config add-authtoken %token%
)

echo.
echo 启动本地服务器和 ngrok 隧道...
start "Flask Server" cmd /c "cd /d %~dp0 && py web/app.py"
timeout /t 3 /nobreak >nul
echo.
echo 正在创建公网隧道...
ngrok http 5000 --host-header="localhost:5000"
goto end

:info
echo.
echo 当前配置:
echo - 本地服务器: http://localhost:5000
echo - 问卷页面: http://localhost:5000/questionnaire
echo - 分享页面: http://localhost:5000/share.html
echo.
echo 局域网访问:
for /f "tokens=2" %%i in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "VPN"') do (
    echo - http://%%i:5000
)
echo.
pause
goto end

:end
pause
