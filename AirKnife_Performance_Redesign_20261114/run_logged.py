"""Keep native stderr in a UTF-8 log without PowerShell error-record formatting."""
import os,subprocess,sys
env=os.environ.copy();env['PYTHONUTF8']='1'
with open(sys.argv[1],'w',encoding='utf-8') as f:
    result=subprocess.run([sys.executable,'-u']+sys.argv[2:],stdout=f,stderr=subprocess.STDOUT,env=env)
raise SystemExit(result.returncode)
