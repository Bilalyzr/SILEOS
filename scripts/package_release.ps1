param(
    [string]$OutputPath = "deliverables/SashaInfinity_Education_OS_Codebase_2026-09-13.zip"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$workspacePrefix = $workspaceRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$deliverablesRoot = [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot "deliverables"))
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $OutputPath))
$deliverablesPrefix = $deliverablesRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $resolvedOutput.StartsWith($deliverablesPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Release archives must be written beneath $deliverablesRoot"
}

if (-not (Test-Path -LiteralPath $deliverablesRoot)) {
    New-Item -ItemType Directory -Path $deliverablesRoot | Out-Null
}

if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}

function Get-WorkspaceRelativePath {
    param([string]$FullName)

    $normalized = [System.IO.Path]::GetFullPath($FullName)
    if (-not $normalized.StartsWith($workspacePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the workspace: $normalized"
    }
    return $normalized.Substring($workspacePrefix.Length)
}

$excludedTopLevel = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(
    ".git", ".local", ".claude", ".zcode",
    ".t", ".t2", ".ta", ".tpay", ".ts", ".tv",
    "sasha_lms", "frontend-build", "uploads", "certificates",
    "certificate-previews", "certificates_render_tmp", "invoices",
    "logs", "recordings", "videos"
) | ForEach-Object { [void]$excludedTopLevel.Add($_) }

$excludedDirectoryNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(
    "node_modules", "dist", "build", ".dart_tool", ".gradle", "Pods",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".coverage", "htmlcov", "backups", "uploads", "certificates",
    "certificate-previews", "certificates_render_tmp", "invoices",
    "ebooks", "logs", "recordings"
) | ForEach-Object { [void]$excludedDirectoryNames.Add($_) }

$excludedFileNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(
    ".secret_key", "youtube_cookies.txt", "sasha_db_20260416.sql",
    "ts_errors.txt", "lms-ss.png", "lms-ss-t.png", "certificate.....png",
    "ure lectureIds always have proper prefix",
    "match - lesson IDs in sections_meta need prefix"
) | ForEach-Object { [void]$excludedFileNames.Add($_) }

$excludedExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(
    ".zip", ".sqlite", ".sqlite3", ".db", ".dump", ".bak",
    ".pem", ".key", ".p12", ".pfx", ".pyc", ".pyo", ".log"
) | ForEach-Object { [void]$excludedExtensions.Add($_) }

$candidateFiles = Get-ChildItem -LiteralPath $workspaceRoot -File -Recurse -Force | Where-Object {
    $relativePath = Get-WorkspaceRelativePath $_.FullName
    $parts = $relativePath -split "[\\/]"

    if ($excludedTopLevel.Contains($parts[0])) { return $false }
    if ($excludedFileNames.Contains($_.Name)) { return $false }
    if ($excludedExtensions.Contains($_.Extension)) { return $false }
    if ($parts | Where-Object { $excludedDirectoryNames.Contains($_) }) { return $false }
    if ($_.Name -match '^\.env(?:$|\.)' -and $_.Name -notmatch '(?i)example') { return $false }
    if ($relativePath -match '^(?i:2025-12-).*\.txt$') { return $false }
    if ($relativePath -ieq "dec_2_changes.txt" -or $relativePath -ieq "gitTok.md") { return $false }
    if ($relativePath -match '^(?i:deliverables)[\\/].*\.sha256\.txt$') { return $false }

    return $true
} | Sort-Object FullName

if (-not ($candidateFiles | Where-Object { $_.Name -eq "SashaInfinity_Education_OS_Product_Document.docx" })) {
    throw "The verified product document is missing from the package inputs."
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$packageRoot = "SashaInfinity_Education_OS"
$fileStream = [System.IO.File]::Open($resolvedOutput, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
$archive = $null

try {
    $archive = [System.IO.Compression.ZipArchive]::new($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)

    foreach ($file in $candidateFiles) {
        $relativePath = (Get-WorkspaceRelativePath $file.FullName).Replace("\", "/")
        $entryName = "$packageRoot/$relativePath"
        $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
        $entry.LastWriteTime = [System.DateTimeOffset]::new($file.LastWriteTime)

        $inputStream = [System.IO.File]::OpenRead($file.FullName)
        $outputStream = $entry.Open()
        try {
            $inputStream.CopyTo($outputStream)
        }
        finally {
            $outputStream.Dispose()
            $inputStream.Dispose()
        }
    }

    $manifestEntry = $archive.CreateEntry("$packageRoot/PACKAGE_CONTENTS.txt", [System.IO.Compression.CompressionLevel]::Optimal)
    $manifestStream = $manifestEntry.Open()
    $writer = [System.IO.StreamWriter]::new($manifestStream, [System.Text.UTF8Encoding]::new($false))
    try {
        $writer.WriteLine("SashaInfinity Education OS source package")
        $writer.WriteLine("Created: 2026-09-13")
        $writer.WriteLine("Files: $($candidateFiles.Count)")
        $writer.WriteLine("")
        $writer.WriteLine("Runtime data, secrets, dependency folders, build output, caches, and the nested duplicate tree are excluded.")
        $writer.WriteLine("")
        foreach ($file in $candidateFiles) {
            $relativePath = (Get-WorkspaceRelativePath $file.FullName).Replace("\", "/")
            $writer.WriteLine($relativePath)
        }
    }
    finally {
        $writer.Dispose()
    }
}
finally {
    if ($null -ne $archive) { $archive.Dispose() }
    $fileStream.Dispose()
}

$result = Get-Item -LiteralPath $resolvedOutput
[PSCustomObject]@{
    Archive = $result.FullName
    Files = $candidateFiles.Count + 1
    SizeBytes = $result.Length
    SizeMB = [math]::Round($result.Length / 1MB, 2)
} | Format-List
