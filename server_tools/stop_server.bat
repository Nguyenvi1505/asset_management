@echo off
echo Dang tim va tat Asset Management Server dang chay ngam...

:: Tat tien trinh Python cua server.py
wmic process where "(name='python.exe' or name='py.exe') and commandline like '%%server.py%%'" call terminate >nul 2>&1

:: Tat file bat dang chay vong lap
wmic process where "name='cmd.exe' and commandline like '%%start_server.bat%%'" call terminate >nul 2>&1

echo.
echo Da tat hoan toan server!
pause
