# Local development worker; run from any directory after installing the model.
$ErrorActionPreference = 'Stop'
$recordingRoot = Split-Path -Parent $PSScriptRoot
$recordingConfig = (Get-Content -Raw -LiteralPath (Join-Path $recordingRoot '.claude/launch.json') | ConvertFrom-Json).configurations[0]
foreach ($recordingEntry in $recordingConfig.env.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($recordingEntry.Name, [string]$recordingEntry.Value, 'Process')
}
$env:TRANSCRIPTION_PYTHON = Join-Path $recordingRoot '.transcription-venv/Scripts/python.exe'
$env:TRANSCRIPTION_MODEL_PATH = Join-Path $recordingRoot 'backend/transcription_models/small'
$env:JITSI_RECORDINGS_DIR = Join-Path $recordingRoot 'backend/recordings_live'
$recordingBackend = Join-Path $recordingRoot 'backend'
Start-Process -FilePath $recordingConfig.runtimeExecutable -ArgumentList '-m app.workers.recording_lessons' -WorkingDirectory $recordingBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $recordingBackend 'recording-worker.log') -RedirectStandardError (Join-Path $recordingBackend 'recording-worker-error.log') -PassThru
