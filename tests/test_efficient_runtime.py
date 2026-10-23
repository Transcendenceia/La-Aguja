"""Regressions for native task completion, bounded code handoff and RAM updates."""
import contextlib,json,os,pty,socket,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import auth,browser,display,gui_session,update_tasks as tasks,updates

class EfficientRuntime(unittest.TestCase):
 def test_root_explorer_is_direct_not_a_settings_page(self):
  with patch.dict(os.environ,{'DISPLAY':':20','XAUTHORITY':'/tmp/private'}),patch('subprocess.call',return_value=0) as call:
   self.assertEqual(gui_session.direct('files'),0)
  argv=call.call_args.args[0];self.assertIn('sudo',argv);self.assertEqual(argv[-2:],['yazi','/']);self.assertNotIn('desk.py',' '.join(argv))
 def test_regular_browser_is_direct_and_waited(self):
  with patch('web.open_browser',return_value=SimpleNamespace(wait=lambda:0)) as opened:
   self.assertEqual(gui_session.direct('browser'),0)
  opened.assert_called_once_with(None)
 def test_codes_require_manual_native_flow_and_matching_state(self):
  record={'url':'https://claude.ai/oauth/authorize?client_id=fixture&state=test-state&response_type=code'}
  code=b'AGUJA-SYNTHETIC-CODE-123456#test-state'
  self.assertEqual(browser.authorization_code(code,record),code)
  for bad in (b'sudo touch /tmp/unsafe',code+b'\nwhoami',code.replace(b'test-state',b'wrong-state'),b'http://example.com/callback?code=123456'):
   self.assertIsNone(browser.authorization_code(bad,record))
  self.assertIsNone(browser.authorization_code(code,None))
  record['url']+='&redirect_uri=http%3A%2F%2Flocalhost%3A1234%2Fcallback'
  self.assertIsNone(browser.authorization_code(code,record))
 def test_code_returns_once_to_existing_pty_and_socket_is_cleaned(self):
  with tempfile.TemporaryDirectory() as tmp:
   directory=Path(tmp);relay=browser.Relay(directory);master,slave=pty.openpty()
   code=b'AGUJA-SYNTHETIC-CODE-123456'
   record={'url':'https://claude.ai/oauth/authorize?client_id=fixture&state=fixture&response_type=code'}
   try:
    with patch.object(auth,'read_record',return_value=record),patch('auth_pty.write_all') as write:
     with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as sender:
      sender.sendto(code,str(directory/'paste.sock'));relay.poll(master)
      sender.sendto(code,str(directory/'paste.sock'));relay.poll(master)
     write.assert_called_once_with(master,code+b'\r')
   finally:relay.close();os.close(master);os.close(slave)
   self.assertFalse((directory/'paste.sock').exists())
 def test_preflight_failure_before_worker_always_cleans_cache(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);stage=root/'stage';run=root/'run';run.mkdir()
   with patch.object(tasks,'STAGE',stage),patch.object(updates,'RUN',run),patch.object(updates,'lock',return_value=contextlib.nullcontext()),patch.object(tasks,'verify_live_ram'),patch.object(tasks,'preflight_session',side_effect=ValueError('SYNTHETIC NO SPACE')),patch.object(updates,'run',return_value=SimpleNamespace(stdout=b'{"filesystems":[{"target":"/","fstype":"overlay"}]}')) as execute:
    result=tasks.session_update([{'id':'package:curl','kind':'package','name':'curl','latest':'1.1'}])
   self.assertFalse(result['ok']);self.assertFalse(result['completed']);self.assertFalse(result['session_may_be_partial'])
   self.assertFalse(list(stage.glob('*/downloads')));self.assertEqual(execute.call_count,1)
 def test_partial_failure_keeps_verified_packages_and_does_not_claim_success(self):
  items=[{'id':'package:curl','kind':'package','name':'curl','current':'1','latest':'2'}]
  with patch.object(tasks,'session_update',return_value={'ok':False,'completed':['package:curl'],'error':'Synthetic harness failure','session_may_be_partial':True}):
   result=tasks.apply(items,{'package:curl':'session'})
  self.assertFalse(result['ok']);self.assertEqual(result['completed'],['package:curl'])
 def test_stale_cleanup_only_removes_named_archives_not_receipts(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);(folder/'build.log').write_text('receipt')
   for name in ('downloads','apt-cache','devices'):(folder/name).mkdir();(folder/name/'file').write_text('cache')
   tasks.clean_session_cache(folder)
   self.assertEqual([p.name for p in folder.iterdir()],['build.log'])

if __name__=='__main__':unittest.main()
