@echo off
chcp 65001 >nul
title AgentBI 智能体控制台 - 前端开发服务器

cd /d "%~dp0"

echo ============================================
echo   AgentBI 智能体控制台 - 前端启动脚本
echo ============================================
echo.

REM 检查 Node.js 环境
where node >nul 2>nul
if %errorlevel% neq 0 (
  echo [错误] 未检测到 Node.js，请先安装 Node.js 22+ 后重试。
  echo        下载地址: https://nodejs.org/
  pause
  exit /b 1
)

REM 检查依赖是否已安装
if not exist "node_modules" (
  echo [初始化] 未检测到 node_modules，正在安装依赖...
  call npm install --no-fund --no-audit
  if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败，请检查网络连接后重试。
    pause
    exit /b 1
  )
  echo.
)

echo [就绪] 启动开发服务器，浏览器将自动打开...
echo [提示] 前端地址: http://localhost:5173
echo [提示] 后端地址: http://127.0.0.1:8000 (需单独启动 AgentBI)
echo.
echo 按 Ctrl+C 可停止服务
echo ============================================
echo.

call npm run dev

pause
