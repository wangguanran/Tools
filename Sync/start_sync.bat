@echo off
cd /d %~dp0
python -m pip install -r requirements.txt

echo Please select sync option:
echo 1. Sync W307 Release
echo 2. Sync W117 TR5 Dev
echo.
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" (
    python remote_sync.py --resource "\\172.16.0.243\wangguanran\Codes\sprd_w307_release" --destination "D:\Codes\sprd_w307_release" --initial-sync --no-watch
) else if "%choice%"=="2" (
    python remote_sync.py --resource "\\172.16.0.243\wangguanran\Codes\sprd_w117_tr5_dev" --destination "D:\Codes\sprd_w117_tr5_dev" --initial-sync --no-watch
) else (
    echo Invalid choice!
)

pause
