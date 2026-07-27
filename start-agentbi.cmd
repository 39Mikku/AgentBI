@echo off
chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-agentbi.ps1" %*
set "AGENTBI_EXIT_CODE=%ERRORLEVEL%"

if not "%AGENTBI_EXIT_CODE%"=="0" (
  echo.
  echo [失败] AgentBI 未能完成启动，请查看上方信息。
  pause
)

exit /b %AGENTBI_EXIT_CODE%
