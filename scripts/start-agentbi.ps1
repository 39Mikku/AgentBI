[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "AgentBI"
$FrontendDir = Join-Path $RepoRoot "Agent-vue"
$VenvDir = Join-Path $RepoRoot "venv"
$BackendUrl = "http://127.0.0.1:8000/"
$FrontendUrl = "http://localhost:5173/"

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
    param(
        [string]$Uri,
        [string]$ExpectedContent
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content -match $ExpectedContent
    }
    catch {
        return $false
    }
}

function Test-AgentBIBackend {
    return (Invoke-HealthProbe -Uri $BackendUrl -ExpectedContent "AgentBI")
}

function Test-AgentBIFrontend {
    return (Invoke-HealthProbe -Uri $FrontendUrl -ExpectedContent "AgentBI")
}

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

    & $python -c "import fastapi, uvicorn, dotenv" *> $null
    $dependenciesReady = $LASTEXITCODE -eq 0
    if ($created -or -not $dependenciesReady) {
        Write-Status "正在安装后端依赖..." Yellow
        & $python -m pip install -r (Join-Path $BackendDir "requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            Stop-WithError "后端依赖安装失败，请检查网络或 requirements.txt。"
        }
    }

    return $python
}

function Install-FrontendEnvironment {
    if (-not (Test-CommandAvailable "node")) {
        Stop-WithError "未检测到 Node.js，请先安装 Node.js 22+ 后重试。"
    }
    if (-not (Test-CommandAvailable "npm.cmd")) {
        Stop-WithError "未检测到 npm，请检查 Node.js 安装。"
    }

    $nodeModules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path -LiteralPath $nodeModules -PathType Container)) {
        Write-Status "未检测到前端依赖，正在执行 npm ci..." Yellow
        Push-Location $FrontendDir
        try {
            & npm.cmd ci --no-fund --no-audit
            if ($LASTEXITCODE -ne 0) {
                Stop-WithError "前端依赖安装失败，请检查网络或 package-lock.json。"
            }
        }
        finally {
            Pop-Location
        }
    }
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Invocation
    )

    $command = 'title {0} && cd /d "{1}" && {2}' -f $Title, $WorkingDirectory, $Invocation
    Start-Process -FilePath $env:ComSpec `
        -ArgumentList @("/d", "/k", $command) `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Normal | Out-Null
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

    $backendHealthy = Test-AgentBIBackend
    if ($backendHealthy) {
        Write-Status "后端已运行，直接复用 http://127.0.0.1:8000" Green
    }
    elseif (Test-PortListening -Port 8000) {
        $backendHealthy = Test-ListeningServiceWithGrace -Port 8000 -Probe ${function:Test-AgentBIBackend}
        if (-not $backendHealthy) {
            Stop-WithError "端口 8000 已被非 AgentBI 服务占用，未启动或终止该进程。"
        }
        Write-Status "后端正在启动，已识别并复用。" Green
    }
    else {
        Write-Status "正在打开后端日志窗口..." Cyan
        $backendInvocation = '"{0}" -m uvicorn AgentBI.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir AgentBI' -f $venvPython
        Start-ServiceWindow `
            -Title "AgentBI Backend" `
            -WorkingDirectory $RepoRoot `
            -Invocation $backendInvocation
    }

    $frontendHealthy = Test-AgentBIFrontend
    if ($frontendHealthy) {
        Write-Status "前端已运行，直接复用 http://localhost:5173" Green
    }
    elseif (Test-PortListening -Port 5173) {
        $frontendHealthy = Test-ListeningServiceWithGrace -Port 5173 -Probe ${function:Test-AgentBIFrontend}
        if (-not $frontendHealthy) {
            Stop-WithError "端口 5173 已被非 AgentBI 服务占用，未启动或终止该进程。"
        }
        Write-Status "前端正在启动，已识别并复用。" Green
    }
    else {
        Write-Status "正在打开前端日志窗口..." Cyan
        Start-ServiceWindow `
            -Title "AgentBI Frontend" `
            -WorkingDirectory $FrontendDir `
            -Invocation "call npm.cmd run dev"
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
