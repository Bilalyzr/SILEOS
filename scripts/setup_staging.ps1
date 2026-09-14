param(
    [switch]$RotateSecrets,
    [switch]$ValidateOnly,
    [switch]$WithCoding
)

$ErrorActionPreference = "Stop"

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runtimeRoot = Join-Path $workspaceRoot ".local\staging"
$envPath = Join-Path $runtimeRoot ".env.staging.local"
$credentialsPath = Join-Path $runtimeRoot "admin-credentials.txt"
$composePath = Join-Path $workspaceRoot "docker-compose.staging.yml"

function New-HexSecret {
    param([int]$Bytes = 32)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([System.BitConverter]::ToString($buffer)).Replace("-", "").ToLowerInvariant()
}

function Write-Utf8NoBom {
    param([string]$Path, [string[]]$Lines)
    [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.UTF8Encoding]::new($false))
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

if ($RotateSecrets -or -not (Test-Path -LiteralPath $envPath)) {
    $adminPassword = "Stg!" + (New-HexSecret 18)
    $envLines = @(
        "COMPOSE_PROJECT_NAME=sasha-staging",
        "RELEASE_TAG=staging-2026-09-13",
        "STAGING_HTTP_PORT=3200",
        "STAGING_BACKEND_PORT=8200",
        "STAGING_STREAMING_PORT=8201",
        "STAGING_POSTGRES_PORT=15433",
        "STAGING_REDIS_PORT=16380",
        "POSTGRES_PASSWORD=$(New-HexSecret)",
        "REDIS_PASSWORD=$(New-HexSecret)",
        "SECRET_KEY=$(New-HexSecret 48)",
        "JWT_SECRET=$(New-HexSecret 48)",
        "AI_CREDENTIAL_ENCRYPTION_KEY=$(New-HexSecret 48)",
        "VIDEO_SECRET=$(New-HexSecret 48)",
        "JITSI_JWT_SECRET=$(New-HexSecret 48)",
        "INTERNAL_TOKEN=$(New-HexSecret 48)",
        "CODE_RUNNER_TOKEN=$(New-HexSecret 48)",
        "ADMIN_EMAIL=staging-admin@example.org",
        "ADMIN_USERNAME=sasha_staging_admin",
        "ADMIN_PASSWORD=$adminPassword",
        "RAZORPAY_KEY=",
        "RAZORPAY_SECRET=",
        "RAZORPAY_WEBHOOK_SECRET=",
        "SMTP_HOST=",
        "SMTP_PORT=587",
        "SMTP_USER=",
        "SMTP_PASSWORD=",
        "EMAIL_FROM=noreply@staging.invalid",
        "BUNNY_LIBRARY_ID=",
        "BUNNY_API_KEY=",
        "BUNNY_CDN_HOSTNAME=",
        "BUNNY_TOKEN_AUTH_KEY=",
        "FIREBASE_API_KEY=",
        "FIREBASE_PROJECT_ID=",
        "VITE_FIREBASE_API_KEY=",
        "VITE_FIREBASE_AUTH_DOMAIN=",
        "VITE_FIREBASE_STORAGE_BUCKET=",
        "VITE_FIREBASE_MESSAGING_SENDER_ID=",
        "VITE_FIREBASE_APP_ID=",
        "JITSI_PUBLIC_URL=https://live.staging.invalid",
        "JUDGE0_URL=",
        "JUDGE0_AUTH_TOKEN="
    )
    Write-Utf8NoBom -Path $envPath -Lines $envLines

    Write-Utf8NoBom -Path $credentialsPath -Lines @(
        "SashaInfinity local staging administrator",
        "URL: http://127.0.0.1:3200/login",
        "Email: staging-admin@example.org",
        "Username: sasha_staging_admin",
        "Password: $adminPassword",
        "Generated: $([DateTime]::UtcNow.ToString('u')) UTC",
        "",
        "This file is local-only and excluded from release packages."
    )
    Write-Output "Generated staging secrets and administrator credentials under .local/staging."
}

# Add newly required values without rotating existing database/signing secrets.
$existingLines = Get-Content -LiteralPath $envPath
$existingLines = @($existingLines | ForEach-Object { $_.Replace('ADMIN_EMAIL=staging-admin@sashainfinity.local', 'ADMIN_EMAIL=staging-admin@example.org') })
if (-not ($existingLines | Where-Object { $_ -match '^AI_CREDENTIAL_ENCRYPTION_KEY=.+' })) {
    $existingLines += "AI_CREDENTIAL_ENCRYPTION_KEY=$(New-HexSecret 48)"
}
Write-Utf8NoBom -Path $envPath -Lines $existingLines
if (Test-Path -LiteralPath $credentialsPath) {
    $credentialLines = @(Get-Content -LiteralPath $credentialsPath | ForEach-Object { $_.Replace('Email: staging-admin@sashainfinity.local', 'Email: staging-admin@example.org') })
    Write-Utf8NoBom -Path $credentialsPath -Lines $credentialLines
}
$composeArgs = @("compose", "--env-file", $envPath, "-f", $composePath)
if ($WithCoding) {
    $judgeLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^JUDGE0_URL=.+' }
    if (-not $judgeLine) {
        throw "Set JUDGE0_URL in $envPath before enabling the coding profile."
    }
    $composeArgs += @("--profile", "coding")
}

& docker @composeArgs config --quiet
if ($LASTEXITCODE -ne 0) { throw "The staging Compose configuration is invalid." }
Write-Output "Staging Compose configuration is valid."

if ($ValidateOnly) {
    Write-Output "Validation-only run complete."
    exit 0
}

& docker info --format "{{.ServerVersion}}" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not ready. Start its Linux engine, then rerun this command."
}

& docker @composeArgs up -d --build
if ($LASTEXITCODE -ne 0) { throw "Staging container startup failed." }

$readyUrl = "http://127.0.0.1:3200/health/ready"
$deadline = [DateTime]::UtcNow.AddMinutes(3)
$ready = $false
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $readyUrl -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    }
    catch { }
    Start-Sleep -Seconds 3
}
if (-not $ready) {
    & docker @composeArgs ps
    & docker @composeArgs logs --tail 120 backend migrate nginx
    throw "Staging did not become ready within three minutes."
}

& docker @composeArgs exec -T backend python seed_admin_simple.py
if ($LASTEXITCODE -ne 0) { throw "Staging administrator creation failed." }

& docker @composeArgs exec -T backend python -m alembic current
if ($LASTEXITCODE -ne 0) { throw "Could not verify the staging migration revision." }

& docker @composeArgs ps
Write-Output "Staging is ready at http://127.0.0.1:3200"
Write-Output "Administrator credentials: $credentialsPath"
Write-Output "Before administrator login, use a private interactive terminal to enroll MFA:"
Write-Output "docker compose --env-file .local/staging/.env.staging.local -f docker-compose.staging.yml exec backend python admin_mfa_enroll.py --email <ADMIN_EMAIL from the local environment>"
