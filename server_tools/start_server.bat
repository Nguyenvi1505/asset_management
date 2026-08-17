@echo off
:: Chuyển đến thư mục gốc của dự án (thư mục cha của file bat)
cd /d "%~dp0\.."



:loop
echo Đang khoi dong Asset Management Server...
py server.py
echo Server bi tat hoac crash! Tu dong khoi dong lai sau 5 giay...
timeout /t 5
goto loop
