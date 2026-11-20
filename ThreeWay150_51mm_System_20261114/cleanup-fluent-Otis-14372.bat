echo off
set LOCALHOST=%COMPUTERNAME%
set KILL_CMD="C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent/ntbin/win64/winkill.exe"

start "tell.exe" /B "C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\tell.exe" Otis 60289 CLEANUP_EXITING
timeout /t 1
"C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\kill.exe" tell.exe
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 28316) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 5444) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 17736) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 23968) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 14372) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 6796)
del "C:\Users\otiso\umbrella\case\ThreeWay150_51mm_System_20261114\cleanup-fluent-Otis-14372.bat"
