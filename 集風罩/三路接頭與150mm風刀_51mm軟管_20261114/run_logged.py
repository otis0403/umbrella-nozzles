"""Keep native stderr in a UTF-8 log without PowerShell error-record formatting."""
import os,subprocess,sys
from pathlib import Path
env=os.environ.copy();env['PYTHONUTF8']='1';env['CFD_ACTIVE_LOG']=str(Path(sys.argv[1]).resolve())
with open(sys.argv[1],'w',encoding='utf-8') as f:
    result=subprocess.run([sys.executable,'-u']+sys.argv[2:],stdout=f,stderr=subprocess.STDOUT,env=env)
raise SystemExit(result.returncode)
