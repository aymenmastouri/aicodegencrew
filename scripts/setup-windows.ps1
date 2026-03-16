# ============================================================================
# setup-windows.ps1 -- Complete SDLC Pilot setup for Windows 10/11
#
# Installs EVERYTHING from scratch: Git, Python 3.12, Node.js 22, clones the
# repo, configures .env, installs all dependencies, and starts the dashboard.
#
# The manager receives ONLY setup-windows.bat (which calls this script)
# and runs it with a double-click -- everything else happens automatically.
#
# Options:
#   -SetupOnly       Setup without starting the dashboard
#   -RunE2E <path>   Setup + run full E2E pipeline on a repository
# ============================================================================

$ErrorActionPreference = 'Stop'

# -- Configuration -- Capgemini Sovereign AI Platform --------------------------
# IMPORTANT: Fill in the API key before distributing this script to managers!
$GIT_REPO_URL      = 'https://bnotkca.pl.s2-eu.capgemini.com/gitlab/ai-group/aicodegencrew.git'
$INSTALL_DIR       = Join-Path $env:USERPROFILE 'aicodegencrew'

$ENV_API_KEY          = 'sk-FILL-IN-BEFORE-DISTRIBUTING'
$ENV_API_BASE         = 'https://litellm.bnotk.sovai-de.apps.ce.capgemini.com/v1'
$ENV_MODEL            = 'openai/code'
$ENV_FAST_MODEL       = 'openai/code'
$ENV_CODEGEN_MODEL    = 'openai/code'
$ENV_VISION_MODEL     = 'openai/vision'
$ENV_EMBED_MODEL      = 'embed'
$ENV_MAX_OUTPUT_TOKENS = '65536'
$ENV_CONTEXT_WINDOW   = '262144'

# -- Helpers ------------------------------------------------------------------

function Log  { param([string]$msg) Write-Host "  [setup] $msg" -ForegroundColor Cyan }
function Ok   { param([string]$msg) Write-Host "    OK $msg" -ForegroundColor Green }
function Warn { param([string]$msg) Write-Host "    ! $msg" -ForegroundColor Yellow }
function Fail { param([string]$msg) Write-Host "    X $msg" -ForegroundColor Red; throw $msg }

function Test-Command { param([string]$cmd) $null = Get-Command $cmd -ErrorAction SilentlyContinue; return $? }

function Refresh-Path {
    $machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath    = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path    = "$machinePath;$userPath"
}

function Install-WithWinget {
    param([string]$packageId, [string]$name)
    Log "Installing $name..."
    winget install --id $packageId --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) {
        Warn "winget returned $LASTEXITCODE for $name -- may already be installed"
    }
    Refresh-Path
}

# -- Banner -------------------------------------------------------------------

Write-Host ''
Write-Host '  =====================================================================' -ForegroundColor Cyan
Write-Host '       SDLC Pilot -- Local Setup (Windows)                              ' -ForegroundColor Cyan
Write-Host '  =====================================================================' -ForegroundColor Cyan
Write-Host ''

# ============================================================================
# STEP 1: Check winget availability
# ============================================================================
Log 'Step 1/7: Checking package manager'

if (-not (Test-Command 'winget')) {
    Fail 'winget not found. Requires Windows 10 1809+ or Windows 11. Install App Installer from Microsoft Store.'
}
Ok 'winget available'

# ============================================================================
# STEP 2: Install Git, Python 3.12, Node.js 22
# ============================================================================
Log 'Step 2/7: Installing software -- Git, Python, Node.js'

# Git
if (-not (Test-Command 'git')) {
    Install-WithWinget 'Git.Git' 'Git'
    Refresh-Path
    if (-not (Test-Command 'git')) { Fail 'Git installation failed' }
}
$gitVer = git --version 2>$null
Ok "Git $gitVer"

# Python 3.12
$pythonCmd = $null
foreach ($candidate in @('python3.12', 'python3', 'python', 'py')) {
    if (Test-Command $candidate) {
        $ver = & $candidate --version 2>&1
        if ("$ver" -match '3\.12') { $pythonCmd = $candidate; break }
    }
}
if (-not $pythonCmd -and (Test-Command 'py')) {
    $ver = py -3.12 --version 2>&1
    if ("$ver" -match '3\.12') { $pythonCmd = 'py -3.12' }
}
if (-not $pythonCmd) {
    Install-WithWinget 'Python.Python.3.12' 'Python 3.12'
    Refresh-Path
    foreach ($candidate in @('python3.12', 'python3', 'python', 'py')) {
        if (Test-Command $candidate) {
            $ver = & $candidate --version 2>&1
            if ("$ver" -match '3\.12') { $pythonCmd = $candidate; break }
        }
    }
    if (-not $pythonCmd -and (Test-Command 'py')) {
        $ver = py -3.12 --version 2>&1
        if ("$ver" -match '3\.12') { $pythonCmd = 'py -3.12' }
    }
    if (-not $pythonCmd) { Fail 'Python 3.12 not found after install. Get it from https://www.python.org/downloads/' }
}
$pyVersion = & ($pythonCmd.Split(' ')[0]) @(($pythonCmd.Split(' ') | Select-Object -Skip 1) + '--version') 2>&1
Ok "Python: $pyVersion"

# Node.js 22
if (-not (Test-Command 'node')) {
    Install-WithWinget 'OpenJS.NodeJS.LTS' 'Node.js 22 LTS'
    Refresh-Path
    if (-not (Test-Command 'node')) { Fail 'Node.js installation failed' }
} else {
    $nodeVer = node --version 2>$null
    $nodeMajor = [int]($nodeVer -replace 'v(\d+)\..*', '$1')
    if ($nodeMajor -lt 18) {
        Install-WithWinget 'OpenJS.NodeJS.LTS' 'Node.js 22 LTS'
        Refresh-Path
    }
}
Ok ('Node.js ' + (node --version 2>$null))
Ok ('npm ' + (npm --version 2>$null))

# ============================================================================
# STEP 3: Clone repository
# ============================================================================
Log 'Step 3/7: Repository'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyprojectPath = Join-Path (Split-Path -Parent $scriptDir) 'pyproject.toml'

if (Test-Path $pyprojectPath) {
    $INSTALL_DIR = Split-Path -Parent $scriptDir
    Ok "Running from inside repo: $INSTALL_DIR"
} elseif (Test-Path (Join-Path $INSTALL_DIR '.git')) {
    Ok "Repository exists at $INSTALL_DIR"
    Push-Location $INSTALL_DIR
    git pull --quiet 2>$null
    if ($LASTEXITCODE -ne 0) { Warn 'git pull failed -- using existing code' }
    Pop-Location
} elseif (Test-Path (Join-Path $INSTALL_DIR 'src\aicodegencrew')) {
    Ok "Project found at $INSTALL_DIR (no .git)"
} else {
    Log 'Cloning repository...'
    Write-Host ''
    Write-Host '  +----------------------------------------------------------+' -ForegroundColor Yellow
    Write-Host '  |  Git will ask for your username + password.              |' -ForegroundColor Yellow
    Write-Host '  |  Please enter your GitLab credentials.                  |' -ForegroundColor Yellow
    Write-Host '  +----------------------------------------------------------+' -ForegroundColor Yellow
    Write-Host ''
    git clone $GIT_REPO_URL $INSTALL_DIR
    if ($LASTEXITCODE -ne 0) { Fail 'git clone failed -- check username/password' }
    Ok "Cloned to $INSTALL_DIR"
}

$ROOT = $INSTALL_DIR

# ============================================================================
# STEP 4: Python virtual environment
# ============================================================================
Log 'Step 4/7: Python environment'

$venvPath = Join-Path $ROOT '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$venvPip = Join-Path $venvPath 'Scripts\pip.exe'

if (-not (Test-Path $venvPython)) {
    Log 'Creating virtual environment...'
    $pyExe = $pythonCmd.Split(' ')[0]
    $pyArgs = @(($pythonCmd.Split(' ') | Select-Object -Skip 1) + '-m' + 'venv' + $venvPath)
    & $pyExe @pyArgs
    if ($LASTEXITCODE -ne 0) { Fail 'venv creation failed' }
    Ok 'Virtual environment created'
} else {
    Ok 'Virtual environment exists'
}

Log 'Installing Python dependencies -- this may take 2-3 minutes...'
& $venvPip install --quiet --upgrade pip setuptools wheel 2>$null
& $venvPip install --quiet -e "$ROOT[dev,parsers]" 2>$null
if ($LASTEXITCODE -ne 0) {
    Warn 'Some optional dependencies failed -- core features should still work'
}
Ok 'Python dependencies installed'

# ============================================================================
# STEP 5: Configure .env
# ============================================================================
Log 'Step 5/7: Configuration (.env)'

$today = Get-Date -Format 'yyyy-MM-dd'
$envLines = @(
    "# SDLC Pilot Configuration -- auto-generated $today",
    '',
    'PROJECT_PATH=C:\path\to\your\repo',
    '',
    'TASK_INPUT_DIR=./inputs/tasks',
    'REQUIREMENTS_DIR=./inputs/requirements',
    'LOGS_DIR=./inputs/logs',
    'REFERENCE_DIR=./inputs/reference',
    '',
    '# LLM Configuration',
    'LLM_PROVIDER=onprem',
    "API_BASE=$ENV_API_BASE",
    "OPENAI_API_KEY=$ENV_API_KEY",
    '',
    "MODEL=$ENV_MODEL",
    "FAST_MODEL=$ENV_FAST_MODEL",
    "CODEGEN_MODEL=$ENV_CODEGEN_MODEL",
    "VISION_MODEL=$ENV_VISION_MODEL",
    '',
    "MAX_LLM_OUTPUT_TOKENS=$ENV_MAX_OUTPUT_TOKENS",
    "LLM_CONTEXT_WINDOW=$ENV_CONTEXT_WINDOW",
    '',
    "EMBED_MODEL=$ENV_EMBED_MODEL",
    '',
    'INDEX_MODE=auto',
    'OUTPUT_DIR=./knowledge/architecture',
    'DOCS_OUTPUT_DIR=./architecture-docs',
    '',
    'LOG_LEVEL=INFO',
    'CREWAI_TRACING_ENABLED=false'
)
$envPath = Join-Path $ROOT '.env'
$envLines -join "`n" | Out-File -FilePath $envPath -Encoding utf8 -Force
Ok '.env configured'

# Validate API key
if ($ENV_API_KEY -eq 'sk-FILL-IN-BEFORE-DISTRIBUTING') {
    Write-Host ''
    Write-Host '  +----------------------------------------------------------+' -ForegroundColor Red
    Write-Host '  |  ERROR: API key not set!                                 |' -ForegroundColor Red
    Write-Host '  |                                                          |' -ForegroundColor Red
    Write-Host '  |  The developer must set the API key in setup-windows.ps1 |' -ForegroundColor Red
    Write-Host '  |  BEFORE distributing the script.                         |' -ForegroundColor Red
    Write-Host '  |  Line 28: $ENV_API_KEY = "sk-..."                        |' -ForegroundColor Red
    Write-Host '  +----------------------------------------------------------+' -ForegroundColor Red
    Write-Host ''
    Fail 'API key placeholder not replaced. Cannot continue.'
}

# ============================================================================
# STEP 6: Frontend dependencies
# ============================================================================
Log 'Step 6/7: Frontend'

Push-Location (Join-Path $ROOT 'ui\frontend')
npm install --silent 2>$null
Pop-Location
Ok 'Frontend dependencies installed'

Push-Location $ROOT
npm install --silent 2>$null
Pop-Location
Ok 'Root dev dependencies installed'

# ============================================================================
# STEP 7: Create directories + verify
# ============================================================================
Log 'Step 7/7: Directories and verification'

foreach ($d in @('logs', 'knowledge', 'inputs\tasks', 'inputs\requirements', 'inputs\logs', 'inputs\reference')) {
    $fullPath = Join-Path $ROOT $d
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    }
}
Ok 'Directory structure ready'

# Verify Python package
$verifyResult = & $venvPython -c 'import aicodegencrew; print("OK")' 2>&1
if ("$verifyResult" -match 'OK') {
    Ok 'aicodegencrew package OK'
} else {
    Warn 'aicodegencrew import check failed'
}

# Verify LLM connectivity
# LLM connectivity check (best-effort)
try {
    $llmCheck = & $venvPython -c 'from aicodegencrew.shared.utils.llm_factory import check_llm_connectivity; print(check_llm_connectivity(timeout=5))' 2>&1
    Ok "LLM check: $llmCheck"
} catch {
    Warn 'LLM connectivity check skipped'
}

# ============================================================================
# DONE -- Summary + convenience scripts
# ============================================================================
Write-Host ''
Write-Host '  =====================================================================' -ForegroundColor Green
Write-Host '                         Setup complete!                                ' -ForegroundColor Green
Write-Host '  =====================================================================' -ForegroundColor Green
Write-Host ''
Write-Host "  Directory:     $ROOT"
Write-Host "  Python:        $pyVersion"
Write-Host ('  Node:          ' + (node --version 2>$null))
Write-Host ('  npm:           ' + (npm --version 2>$null))
Write-Host ''
Write-Host '  Start dashboard:' -ForegroundColor White
Write-Host "    cd $ROOT" -ForegroundColor Cyan
Write-Host '    ./scripts/dev.sh' -ForegroundColor Cyan
Write-Host ''
Write-Host '  Stop dashboard:' -ForegroundColor White
Write-Host '    ./scripts/dev.sh stop' -ForegroundColor Cyan
Write-Host ''
Write-Host '  (Run these in Git Bash, which was installed in Step 2)' -ForegroundColor DarkGray
Write-Host ''
