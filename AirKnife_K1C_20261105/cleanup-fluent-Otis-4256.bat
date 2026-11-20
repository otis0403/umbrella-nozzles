echo off
set LOCALHOST=%COMPUTERNAME%
set KILL_CMD="C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent/ntbin/win64/winkill.exe"

start "tell.exe" /B "C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\tell.exe" Otis 55508 CLEANUP_EXITING
timeout /t 1
"C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\kill.exe" tell.exe
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 26424) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 12448) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 26996) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 4732) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 4256) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 7984)
del "C:\Users\otiso\umbrella\case\AirKnife_K1C_20261105\cleanup-fluent-Otis-4256.bat"
