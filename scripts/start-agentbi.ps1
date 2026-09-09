[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$SetupOnly,
    [switch]$Hidden,
    [ValidateRange(1, 65535)][int]$BackendPort = 8000,
    [ValidateRange(1, 65535)][int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "AgentBI"
$FrontendDir = Join-Path $RepoRoot "Agent-vue"
$VenvDir = Join-Path $RepoRoot "venv"
if (Test-Path -LiteralPath (Join-Path $RepoRoot ".venv")) { $VenvDir = Join-Path $RepoRoot ".venv" }
$BackendUrl = "http://127.0.0.1:$BackendPort/"
$FrontendUrl = "http://localhost:$FrontendPort/"

function Write-Status {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    Write-Host "[AgentBI] $Message" -ForegroundColor $Color
}

function Stop-WithError {
    param([string]$Message)

    throw $Message
}

function Test-CommandAvailable {
    param([string]$Name)

    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-PortListening {
    param([int]$Port)

    if (Test-CommandAvailable "Get-NetTCPConnection") {
        try {
            $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
                Select-Object -First 1
            if ($null -ne $listener) {
                return $true
            }
        }
        catch {
            # Fall through to netstat for restricted Windows environments.
        }
    }

    $match = netstat -ano -p TCP 2>$null |
        Select-String -Pattern (":{0}\s+.*LISTENING" -f $Port) |
        Select-Object -First 1
    return $null -ne $match
}

function Invoke-HealthProbe {
    param([string]$Uri)
    try {
        $response = Invoke-RestMethod -Uri $Uri -TimeoutSec 2
        return $response.instance -and ([IO.Path]::GetFullPath($response.instance).TrimEnd('\', '/') -eq $RepoRoot.TrimEnd('\', '/'))
    }
    catch { return $false }
}

function Test-AgentBIBackend { return (Invoke-HealthProbe -Uri $BackendUrl) }
function Test-AgentBIFrontend { return (Invoke-HealthProbe -Uri ($FrontendUrl + "__agentbi")) }

function Wait-ServiceReady {
    param(
        [scriptblock]$Probe,
        [string]$Name,
        [int]$TimeoutSeconds = 60
    )

    $timer = [Diagnostics.Stopwatch]::StartNew()
    Write-Host ("[AgentBI] 等待{0}就绪" -f $Name) -NoNewline -ForegroundColor Cyan
    while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        if (& $Probe) {
            Write-Host " 完成" -ForegroundColor Green
            return
        }
        Write-Host "." -NoNewline -ForegroundColor DarkGray
        Start-Sleep -Milliseconds 500
    }
    Write-Host
    Stop-WithError ("{0}在 {1} 秒内未就绪，请查看对应日志窗口。" -f $Name, $TimeoutSeconds)
}

function Resolve-VenvPython {
    $rootPython = Join-Path $VenvDir "python.exe"
    $scriptsPython = Join-Path $VenvDir "Scripts\python.exe"
    $candidates = @($rootPython, $scriptsPython)

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    return $null
}

function Install-BackendEnvironment {
    $python = Resolve-VenvPython
    $created = $false

    if (-not $python) {
        if (Test-Path -LiteralPath $VenvDir) {
            Stop-WithError "venv 目录已存在，但未找到 python.exe。请检查或移走损坏的环境后重试。"
        }

        Write-Status "未检测到 Python 环境，正在创建 venv..." Yellow
        if (Test-CommandAvailable "py") {
            & py -3 -m venv $VenvDir
        }
        elseif (Test-CommandAvailable "python") {
            & python -m venv $VenvDir
        }
        else {
            Stop-WithError "未检测到 Python 3，请先安装 Python 后重试。"
        }
        if ($LASTEXITCODE -ne 0) {
            Stop-WithError "Python 虚拟环境创建失败。"
        }

        $python = Resolve-VenvPython
        if (-not $python) {
            Stop-WithError "虚拟环境已创建，但未找到可执行的 python.exe。"
        }
        $created = $true
    }

    & $python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) { Stop-WithError "需要 Python 3.11+，推荐使用已验证的 Python 3.13。" }
    $requirements = Join-Path $BackendDir "requirements-lock.txt"
    $manifest = Join-Path $BackendDir "requirements.txt"
    $stamp = Join-Path $VenvDir ".agentbi-requirements.sha256"
    $hash = (Get-FileHash $requirements).Hash + (Get-FileHash $manifest).Hash
    # Windows PowerShell 5.1 turns native stderr into errors even when redirected.
    $ErrorActionPreference = "Continue"
    try {
        & $python -c "import tzdata, fastapi, uvicorn, pydantic, openai, langchain, langchain_openai, httpx, bs4, html2text, docx, python_multipart, dotenv, websockets" *> $null
        $dependenciesReady = $LASTEXITCODE -eq 0
        if ($dependenciesReady) {
            & $python -m pip check *> $null
            $dependenciesReady = $LASTEXITCODE -eq 0
        }
    }
    finally { $ErrorActionPreference = "Stop" }
    $unchanged = (Test-Path -LiteralPath $stamp) -and ((Get-Content -LiteralPath $stamp -Raw).Trim() -eq $hash)
    if ($created -or -not $dependenciesReady -or -not $unchanged) {
        Write-Status "正在同步后端锁定依赖..." Yellow
        & $python -m pip install -r $requirements -r $manifest | Out-Host
        if ($LASTEXITCODE -ne 0) { Stop-WithError "后端依赖安装失败，请查看上方输出。" }
        Set-Content -LiteralPath $stamp -Value $hash -Encoding ASCII
    }

    return $python
}

function Install-NodeDependencies {
    param([string]$Directory)
    $lock = Join-Path $Directory "package-lock.json"
    $hash = (Get-FileHash $lock).Hash + (Get-FileHash (Join-Path $Directory "package.json")).Hash
    $stamp = Join-Path $Directory "node_modules\.agentbi-lock.sha256"
    $ready = (Test-Path -LiteralPath $stamp) -and ((Get-Content -LiteralPath $stamp -Raw).Trim() -eq $hash)
    Push-Location $Directory
    try {
        if ($ready) {
            $ErrorActionPreference = "Continue"
            try {
                & npm.cmd ls --depth=0 *> $null
                $ready = $LASTEXITCODE -eq 0
            }
            finally { $ErrorActionPreference = "Stop" }
        }
        if (-not $ready) {
            Write-Status "正在同步 Node 依赖：$Directory" Yellow
            & npm.cmd ci --no-fund --no-audit | Out-Host
            if ($LASTEXITCODE -ne 0) { Stop-WithError "Node 依赖安装失败：$Directory" }
            Set-Content -LiteralPath $stamp -Value $hash -Encoding ASCII
        }
    }
    finally { Pop-Location }
}

function Install-FrontendEnvironment {
    if (-not (Test-CommandAvailable "node") -or -not (Test-CommandAvailable "npm.cmd")) {
        Stop-WithError "需要 Node.js 22.18+（22.x）或 24.12+，以及 npm。"
    }
    & node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit((a===22&&b>=18)||(a===24&&b>=12)||a>24?0:1)"
    if ($LASTEXITCODE -ne 0) { Stop-WithError "Node 版本需要满足 ^22.18.0 或 >=24.12.0。" }
    Install-NodeDependencies -Directory $FrontendDir
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Invocation
    )

    $command = 'title {0} && cd /d "{1}" && {2}' -f $Title, $WorkingDirectory, $Invocation
    if ($Hidden) {
        $logDir = Join-Path $BackendDir "logs"
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        $process = Start-Process -FilePath $env:ComSpec -ArgumentList @("/d", "/c", $command) -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir "$Title.stdout.log") -RedirectStandardError (Join-Path $logDir "$Title.stderr.log")
        Write-Status ("后台进程 PID {0}，日志：{1}" -f $process.Id, $logDir)
    }
    else {
        Start-Process -FilePath $env:ComSpec -ArgumentList @("/d", "/k", $command) -WorkingDirectory $WorkingDirectory -WindowStyle Normal | Out-Null
    }
}

function Test-ListeningServiceWithGrace {
    param(
        [int]$Port,
        [scriptblock]$Probe
    )

    if (-not (Test-PortListening -Port $Port)) {
        return $false
    }

    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        if (& $Probe) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

try {
    Write-Host
    Write-Host "============================================" -ForegroundColor DarkGray
    Write-Host "  AgentBI 本地工作台 · 一键启动" -ForegroundColor White
    Write-Host "============================================" -ForegroundColor DarkGray
    Write-Host

    if (-not (Test-Path -LiteralPath $BackendDir -PathType Container) -or
        -not (Test-Path -LiteralPath $FrontendDir -PathType Container)) {
        Stop-WithError "脚本必须位于完整的 AgentBI 仓库中。"
    }

    $envPath = Join-Path $BackendDir ".env"
    if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
        $envExample = Join-Path $BackendDir ".env.example"
        if (-not (Test-Path -LiteralPath $envExample -PathType Leaf)) {
            Stop-WithError "缺少 AgentBI\.env 和 AgentBI\.env.example。"
        }
        Copy-Item -LiteralPath $envExample -Destination $envPath
        Write-Status "已从 .env.example 创建 AgentBI\.env；第三方密钥可稍后补充。" Yellow
    }

    $venvPython = Install-BackendEnvironment
    Install-FrontendEnvironment
    $musicEnabled = & $venvPython -c "from dotenv import dotenv_values; import os, sys; c=dotenv_values(sys.argv[1]); print(os.environ.get('NCM_ENABLED', c.get('NCM_ENABLED', 'true')).strip().lower())" $envPath
    if ($musicEnabled -notin @("false", "0", "no", "off")) {
        Install-NodeDependencies -Directory (Join-Path $BackendDir "vendor\netease-music-api")
    }
    if ($SetupOnly) {
        Write-Status "依赖初始化完成。" Green
        exit 0
    }
    $env:AGENTBI_BACKEND_URL = $BackendUrl.TrimEnd('/')

    $backendHealthy = Test-AgentBIBackend
    if ($backendHealthy) {
        Write-Status "后端已运行，直接复用 $BackendUrl" Green
    }
    elseif (Test-PortListening -Port $BackendPort) {
        $backendHealthy = Test-ListeningServiceWithGrace -Port $BackendPort -Probe ${function:Test-AgentBIBackend}
        if (-not $backendHealthy) {
            Stop-WithError "端口 $BackendPort 已被非 AgentBI 服务占用，未启动或终止该进程。"
        }
        Write-Status "后端正在启动，已识别并复用。" Green
    }
    else {
        Write-Status "正在启动后端..." Cyan
        $backendInvocation = '"{0}" -m uvicorn AgentBI.main:app --host 127.0.0.1 --port {1} --reload --reload-dir AgentBI' -f $venvPython, $BackendPort
        Start-ServiceWindow `
            -Title "AgentBI Backend" `
            -WorkingDirectory $RepoRoot `
            -Invocation $backendInvocation
    }

    $frontendHealthy = Test-AgentBIFrontend
    if ($frontendHealthy) {
        Write-Status "前端已运行，直接复用 $FrontendUrl" Green
    }
    elseif (Test-PortListening -Port $FrontendPort) {
        $frontendHealthy = Test-ListeningServiceWithGrace -Port $FrontendPort -Probe ${function:Test-AgentBIFrontend}
        if (-not $frontendHealthy) {
            Stop-WithError "端口 $FrontendPort 已被非 AgentBI 服务占用，未启动或终止该进程。"
        }
        Write-Status "前端正在启动，已识别并复用。" Green
    }
    else {
        Write-Status "正在启动前端..." Cyan
        Start-ServiceWindow `
            -Title "AgentBI Frontend" `
            -WorkingDirectory $FrontendDir `
            -Invocation "call npm.cmd run dev -- --port $FrontendPort"
    }

    Wait-ServiceReady -Probe ${function:Test-AgentBIBackend} -Name "后端"
    Wait-ServiceReady -Probe ${function:Test-AgentBIFrontend} -Name "前端"

    Write-Host
    Write-Status "工作台已就绪：$FrontendUrl" Green
    Write-Status "关闭 Backend / Frontend 日志窗口即可停止对应服务。" DarkGray
    if (-not $NoBrowser) {
        Start-Process $FrontendUrl
    }
    exit 0
}
catch {
    Write-Host
    Write-Host ("[错误] {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
