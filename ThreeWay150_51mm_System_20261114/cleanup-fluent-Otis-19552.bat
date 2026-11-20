echo off
set LOCALHOST=%COMPUTERNAME%
set KILL_CMD="C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent/ntbin/win64/winkill.exe"

start "tell.exe" /B "C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\tell.exe" Otis 49278 CLEANUP_EXITING
timeout /t 1
"C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\kill.exe" tell.exe
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 20920) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 27824) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 18616) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 25932) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 19552) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 10572)
del "C:\Users\otiso\umbrella\case\ThreeWay150_51mm_System_20261114\cleanup-fluent-Otis-19552.bat"
