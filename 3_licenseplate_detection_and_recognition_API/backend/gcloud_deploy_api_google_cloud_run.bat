@echo off
setlocal EnableExtensions

set "GOOGLE_CLOUD_PROJECT_NAME=vistoria-ocr-v1"
set "GOOGLE_CLOUD_SERVICE_NAME=vistoria-ocr-api"

REM Deploy docker container at Google Cloud Run
gcloud run deploy "%GOOGLE_CLOUD_SERVICE_NAME%" --project "%GOOGLE_CLOUD_PROJECT_NAME%" --source . --min-instances 1 --memory 4Gi --cpu 2

pause
endlocal