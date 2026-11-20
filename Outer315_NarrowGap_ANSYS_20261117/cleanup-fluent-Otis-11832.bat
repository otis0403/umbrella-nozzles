echo off
set LOCALHOST=%COMPUTERNAME%
set KILL_CMD="C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent/ntbin/win64/winkill.exe"

start "tell.exe" /B "C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\tell.exe" Otis 56929 CLEANUP_EXITING
timeout /t 1
"C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\kill.exe" tell.exe
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 30668) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 18284) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 19636) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 17240) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 11832) 
if /i "%LOCALHOST%"=="Otis" (%KILL_CMD% 11464)
del "C:\Users\otiso\umbrella\case\Outer315_NarrowGap_ANSYS_20261117\cleanup-fluent-Otis-11832.bat"
