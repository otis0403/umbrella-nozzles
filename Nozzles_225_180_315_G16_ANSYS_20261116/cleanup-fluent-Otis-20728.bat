echo off
set LOCALHOST=%COMPUTERNAME%
set KILL_CMD="C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent/ntbin/win64/winkill.exe"

start "tell.exe" /B "C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\tell.exe" Otis 57883 CLEANUP_EXITING
timeout /t 1
"C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\kill.exe" tell.exe
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 20556) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 10416) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 10764) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 18672) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 20728) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 25796)
del "C:\Users\otiso\umbrella\case\Nozzles_225_180_315_G16_ANSYS_20261116\cleanup-fluent-Otis-20728.bat"
