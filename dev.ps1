# Starts the full dev stack: backend (uvicorn via .venv) + frontend (vite).
# Backend runs in a separate window; frontend runs in this one (Ctrl+C stops it).

$root = $PSScriptRoot

$uvicorn = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    Write-Error "uvicorn not found at $uvicorn - is the venv set up? (cd backend; uv sync --locked --extra dev)"
    exit 1
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root\backend'; & '$uvicorn' main:app --reload"
) -WindowStyle Normal

Set-Location (Join-Path $root "frontend")
npm run dev
