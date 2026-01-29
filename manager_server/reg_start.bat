@echo off

if "%1"=="hide" goto begin
start mshta vbscript:createobject("wscript.shell").run("""%~0"" hide",0)(window.close)&&exit
:begin


cd /d "D:\yjq\manager_server"

start /b manager_server.exe

exit