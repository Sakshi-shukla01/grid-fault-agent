# build.ps1 — run this instead of docker build

$ErrorActionPreference = "Stop"

Write-Host "Setting Docker environment..."
$env:DOCKER_BUILDKIT = "0"
$env:COMPOSE_HTTP_TIMEOUT = "500"
$env:DOCKER_CLIENT_TIMEOUT = "500"

function Build-Image {
    param($dockerfile, $tag, $context)
    Write-Host "`nBuilding $tag ..." -ForegroundColor Cyan
    $maxRetries = 3
    $retryCount = 0
    while ($retryCount -lt $maxRetries) {
        try {
            docker build -f $dockerfile -t $tag $context
            if ($LASTEXITCODE -eq 0) {
                Write-Host "SUCCESS: $tag built" -ForegroundColor Green
                return
            }
        } catch {
            Write-Host "Attempt $($retryCount+1) failed: $_" -ForegroundColor Yellow
        }
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "Retrying in 10 seconds..."
            Start-Sleep -Seconds 10
            Write-Host "Restarting WSL..."
            wsl --shutdown
            Start-Sleep -Seconds 5
        }
    }
    Write-Host "FAILED after $maxRetries attempts: $tag" -ForegroundColor Red
}

Build-Image "Dockerfile.env"       "sakshishukla10/grid-fault-env:latest"       "."
Build-Image "Dockerfile.inference" "sakshishukla10/grid-fault-inference:latest" "."
Build-Image "Dockerfile.worker"    "sakshishukla10/grid-fault-worker:latest"    "."
Build-Image "server/Dockerfile"    "sakshishukla10/grid-fault-dashboard:latest" "./server"

Write-Host "`nAll images built. Pushing to DockerHub..." -ForegroundColor Cyan
docker push sakshishukla10/grid-fault-env:latest
docker push sakshishukla10/grid-fault-inference:latest
docker push sakshishukla10/grid-fault-worker:latest
docker push sakshishukla10/grid-fault-dashboard:latest

Write-Host "`nDone! Check https://hub.docker.com/u/sakshishukla10" -ForegroundColor Green