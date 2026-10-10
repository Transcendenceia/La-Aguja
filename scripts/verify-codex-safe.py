#!/usr/bin/env python3
"""Verify the installed Codex Safe policy and real sandbox without AI inference."""
import sys,subprocess,json,select,time,tempfile,pathlib
sys.path.insert(0,'/usr/lib/aguja');import harness
_,args,_=harness.invocation('codex','safe')
configs=[]
for i,a in enumerate(args):
 if a=='-c':configs.extend([a,args[i+1]])
configs+=['-c','sandbox_mode='+json.dumps(args[args.index('--sandbox')+1]),'-c','approval_policy='+json.dumps(args[args.index('--ask-for-approval')+1])]
base=pathlib.Path(tempfile.mkdtemp(prefix='aguja-final-sandbox-',dir='/home/aguja'));work=base/'workspace';work.mkdir()
probe="import pathlib,subprocess,socket,json; r={}; pathlib.Path('inside').write_text('fixture'); r['workspace_write']=True;\ntry: pathlib.Path("+repr(str(base/'outside'))+").write_text('fixture'); r['outside_write_blocked']=False\nexcept OSError: r['outside_write_blocked']=True\np=subprocess.run(['sudo','-n','id'],capture_output=True);r['sudo_blocked']=p.returncode!=0\ntry: s=socket.socket();s.bind(('127.0.0.1',0));r['network_blocked']=False;s.close()\nexcept OSError:r['network_blocked']=True\nprint(json.dumps(r))"
p=subprocess.Popen(['codex','app-server','--stdio']+configs,cwd=work,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
def request(i,method,params):
 p.stdin.write(json.dumps({'id':i,'method':method,'params':params})+'\n');p.stdin.flush()
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  if not select.select([p.stdout],[],[],1)[0]:continue
  line=p.stdout.readline()
  if not line:raise RuntimeError('server stopped')
  o=json.loads(line)
  if o.get('id')==i:
   if 'error' in o:raise RuntimeError(str(o['error']))
   return o['result']
 raise RuntimeError('timeout')
try:
 request(1,'initialize',{'clientInfo':{'name':'aguja-final-check','version':'1'},'capabilities':{'experimentalApi':True}})
 p.stdin.write('{"method":"initialized","params":{}}\n');p.stdin.flush()
 r=request(2,'thread/start',{'cwd':str(work),'ephemeral':True})
 policy={k:r[k] for k in ['approvalPolicy','approvalsReviewer','sandbox']}
 assert policy['approvalPolicy']=='on-request' and policy['approvalsReviewer']=='user'
 assert policy['sandbox']['type']=='workspaceWrite' and not policy['sandbox']['networkAccess']
 r=request(3,'command/exec',{'command':['python3','-c',probe],'timeoutMs':10000})
 assert r['exitCode']==0,r
 boundary=json.loads(r['stdout']);assert all(boundary.values()),boundary
 sudo=subprocess.run(['sudo','-n','id','-u'],capture_output=True,text=True)
 assert sudo.returncode==0 and sudo.stdout.strip()=='0'
 print(json.dumps({'policy':policy,'native_sandbox':boundary,'os_sudo_unchanged':True,'codex_version':subprocess.check_output(['codex','--version'],text=True).strip(),'live_harness_sha256':__import__('hashlib').sha256(pathlib.Path(harness.__file__).read_bytes()).hexdigest(),'no_model_turns':True}))
finally:p.terminate();p.wait(timeout=5)
