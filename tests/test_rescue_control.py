import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
import approval_broker
import cockpit
import harness
import panel_state
import profile


class RescueControlTests(unittest.TestCase):
    def test_default_view_and_repeated_enter_choose_safe_not_yolo(self):
        self.assertEqual(panel_state.PanelState().view,'help')
        class Screen:
            def timeout(self,value):pass
            def getch(self):return 13
            def erase(self):pass
            def getmaxyx(self):return 24,120
            def addnstr(self,*args):pass
            def refresh(self):pass
        with patch.object(cockpit.sys.stdin,'isatty',return_value=True),patch.object(cockpit.curses,'wrapper',side_effect=lambda fn:fn(Screen())):
            for name in harness.BINS:
                self.assertEqual(harness.choose_mode(name),'safe')
        with patch.object(cockpit.sys.stdin,'isatty',return_value=False):
            self.assertIsNone(harness.choose_mode('codex'))

    def test_safe_arguments_cannot_silently_override_permissions(self):
        for name in harness.BINS:
            for flag in ['--dangerously-skip-permissions','--config','--auto','-c']:
                with self.assertRaises(ValueError):harness.invocation(name,'safe',[flag])
            _,args,env=harness.invocation(name,'unsafe')
            self.assertEqual(env['AGUJA_EXECUTION_MODE'],'unsafe')
        _,safe,env=harness.invocation('codex','safe')
        self.assertTrue(any('approval_hook.py' in a for a in safe))
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',safe)
        self.assertEqual(safe[safe.index('--sandbox')+1],'workspace-write')
        self.assertEqual(safe[safe.index('--ask-for-approval')+1],'on-request')
        self.assertIn('sandbox_workspace_write.network_access=false',safe)
        self.assertIn('sandbox_workspace_write.writable_roots=[]',safe)
        self.assertIn('approvals_reviewer="user"',safe)
        self.assertNotIn('danger-full-access',safe)
        for flag in ['--approve-for-me','--full-auto','--profile=automatic','--permission-profile=full',
                     '--add-dir=/','--cd=/','-capproval_policy="never"','-sdanger-full-access',
                     '-anever','-pautomatic','-Pfull','-C/']:
            with self.assertRaises(ValueError):harness.invocation('codex','safe',[flag])
        _,unsafe,_=harness.invocation('codex','unsafe')
        self.assertIn('--dangerously-bypass-approvals-and-sandbox',unsafe)
        _,_,env=harness.invocation('opencode','safe')
        self.assertEqual(json.loads(env['OPENCODE_CONFIG_CONTENT'])['permission'],{'*':'ask'})

    def test_antigravity_asks_all_actions_without_losing_model_api_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            settings=Path(folder)/'.gemini/antigravity-cli/settings.json'
            settings.parent.mkdir(parents=True)
            settings.write_text('{"modelProvider":"gemini","model":"fixture-model"}')
            harness.configure('antigravity','safe',folder)
            result=json.loads(settings.read_text())
            self.assertEqual(result['modelProvider'],'gemini')
            self.assertEqual(result['model'],'fixture-model')
            self.assertIn('command(*)',result['permissions']['ask'])
            self.assertIn('write_file(*)',result['permissions']['ask'])

    def test_public_locale_overrides_factory_even_before_unlock_and_rejects_injection(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);(base/'config').mkdir()
            selection={'language':'en_US.UTF-8','keyboard':'us','variant':'intl'}
            (base/'config/aguja-locale.json').write_text(json.dumps(selection))
            calls=[]
            self.assertEqual(profile.apply_locale(None,root=base,runner=lambda args,**kwargs:calls.append(args)),selection)
            self.assertEqual(calls,[['setupcon','--keyboard-only','--save','--force']])
            self.assertIn('XKBLAYOUT="us"',(base/'etc/default/keyboard').read_text())
            (base/'config/aguja-locale.json').write_text('{"language":"$(touch /tmp/invalid)"}')
            self.assertEqual(profile.apply_locale(None,root=base,runner=lambda *a,**k:None),profile.DEFAULT_LOCALE)

    def test_visible_console_helper_rejects_non_vt_and_inactive_terminal(self):
        import console_mode
        with patch.object(console_mode.os,'geteuid',return_value=0),patch.object(console_mode.Path,'read_text',return_value='tty1'):
            for args in [[],['/dev/sda','1'],['/dev/pts/0','1'],['/dev/tty2','1'],['/dev/tty1','3']]:
                self.assertEqual(console_mode.main(args),1)
        with patch.object(console_mode.os,'geteuid',return_value=1000):
            self.assertEqual(console_mode.main(['/dev/tty1','1']),1)

    def test_locked_private_tailnet_state_does_not_block_rescue_home(self):
        import network
        with patch.object(network,'output',return_value=''),patch.object(network,'session',return_value={'ssh_auth_mode':'locked'}),patch.object(network.Path,'is_file',side_effect=PermissionError):
            state=network.state()
        self.assertEqual(state['ssh_auth_mode'],'locked')
        self.assertIsNone(state['tailscale'])

    def test_factory_password_encrypts_and_wrong_password_does_not_unlock(self):
        capsule={'schema':1,'hostname':'aguja','network':{'ethernet':{'method':'auto'}},
                 'ssh':{'password':'synthetic-ssh','public_key':'','port':22},'providers':{},'remote':{'enabled':False}}
        sealed=profile.seal(capsule,{'mode':'encrypted','passphrase':'aguja'})
        self.assertNotIn(b'synthetic-ssh',sealed)
        self.assertIsNone(profile.open_capsule(sealed))
        self.assertEqual(profile.open_capsule(sealed,'aguja')['ssh']['password'],'synthetic-ssh')
        with self.assertRaises(Exception):profile.open_capsule(sealed,'wrong')


class ApprovalGateTests(unittest.TestCase):
    def test_hook_without_live_human_channel_denies(self):
        result=subprocess.run([sys.executable,str(ROOT/'runtime/approval_hook.py')],input='{"tool_name":"Bash","tool_input":{"command":"touch /tmp/no"}}',text=True,capture_output=True,env=dict(os.environ,AGUJA_APPROVAL_SOCKET='/nonexistent/socket'))
        self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'],'deny')

    def test_real_pty_hook_requires_visible_fresh_confirmation_before_side_effect(self):
        import pty,select,time
        for answer,allowed in [(b'\n',False),(b'yes\n',True)]:
            with tempfile.TemporaryDirectory() as folder:
                effect=Path(folder)/'confirmed-task'
                child=("import sys,subprocess,json,pathlib; result=subprocess.run([sys.executable,"+repr(str(ROOT/'runtime/approval_hook.py'))+"],input=json.dumps({'tool_name':'Bash','tool_input':{'command':'create synthetic fixture'}}),text=True,capture_output=True); approved=json.loads(result.stdout)=={}; pathlib.Path("+repr(str(effect))+").write_text('approved') if approved else None; print('TASK_ALLOWED='+str(approved),flush=True)")
                parent="import sys,os,pathlib;sys.path.insert(0,"+repr(str(ROOT/'runtime'))+");import auth,auth_pty;auth.BASE=pathlib.Path("+repr(folder)+");os.environ['AGUJA_EXECUTION_MODE']='safe';raise SystemExit(auth_pty.run([sys.executable,'-c',"+repr(child)+"],'codex'))"
                master,slave=pty.openpty();process=subprocess.Popen([sys.executable,'-c',parent],stdin=slave,stdout=slave,stderr=slave);os.close(slave)
                os.write(master,b'\n\n');output=bytearray();sent=False;deadline=time.monotonic()+8
                try:
                    while time.monotonic()<deadline:
                        if select.select([master],[],[],.1)[0]:
                            try:part=os.read(master,65536)
                            except OSError:break
                            if not part:break
                            output.extend(part)
                            if b'> ' in output and not sent:
                                self.assertFalse(effect.exists());os.write(master,answer);sent=True
                        if process.poll() is not None:break
                    process.wait(timeout=2)
                    self.assertEqual(process.returncode,0,output.decode(errors='replace'))
                    self.assertTrue(sent);self.assertEqual(effect.exists(),allowed)
                    self.assertIn(('TASK_ALLOWED='+str(allowed)).encode(),output)
                finally:
                    os.close(master)
                    if process.poll() is None:process.terminate();process.wait(timeout=2)

    def test_gate_requires_fresh_affirmation_not_queued_enter_and_masks_values(self):
        for answer,expected in [(b'\n',b'deny\n'),(b'yes\n',b'approve\n')]:
            with tempfile.TemporaryDirectory() as folder:
                broker=approval_broker.Broker(Path(folder));read_fd,write_fd=os.pipe();output=[];received=[]
                os.write(write_fd,b'\n\n')
                def client():
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
                        c.connect(str(broker.path));c.sendall(b'{"tool_name":"Bash","tool_input":{"command":"printf hello; TOKEN=synthetic"}}\n');received.append(c.recv(20))
                thread=threading.Thread(target=client);thread.start()
                def visible(data):
                    output.append(data)
                    if data.endswith(b'> '):os.write(write_fd,answer)
                import select
                select.select([broker.listener],[],[],1)
                broker.poll(visible,read_fd);thread.join(timeout=2)
                self.assertEqual(received,[expected])
                self.assertNotIn(b'TOKEN=synthetic',b''.join(output))
                self.assertIn(b'printf hello',b''.join(output))
                broker.close();os.close(read_fd);os.close(write_fd)


if __name__=='__main__':unittest.main()
