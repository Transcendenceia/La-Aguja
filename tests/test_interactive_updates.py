import contextlib,hashlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import updates as u, update_tasks as tasks, update_ui as ui, update_progress as progress, update_sources as sources

class Selection(unittest.TestCase):
 def setUp(self):
  self.items=tasks.rows({'packages':[{'name':'curl','current':'1.0','latest':'1.1'},{'name':'openssl','current':'2.0','latest':'2.1'}],'harnesses':{'codex':{'current':'1.0.0','latest':'1.1.0','available':True,'candidate':{'version':'1.1.0','url':'https://github.com/openai/codex/releases/download/rust-v1.1.0/file','algorithm':'sha256','digest':'a'*64,'member':'codex'}}},'release':{'current':'1.0.0','latest':'1.0.1','available':True}})
 def test_no_means_no_installer_or_usb_operation(self):
  with patch.object(u,'package_generation') as persistent,patch.object(tasks,'session_update') as temporary:
   result=tasks.apply(self.items,{r['id']:'no' for r in self.items})
  self.assertTrue(result['no_changes']);persistent.assert_not_called();temporary.assert_not_called()
 def test_selection_only_installs_requested_session_items_without_usb_fallback(self):
  choices={'package:curl':'session','harness:codex':'session'}
  with patch.object(u,'package_generation') as persistent,patch.object(tasks,'session_update',return_value={'ok':True,'completed':['package:curl','harness:codex']}) as temporary:
   result=tasks.apply(self.items,choices)
  self.assertTrue(result['ok']);persistent.assert_not_called()
  self.assertEqual([r['id'] for r in temporary.call_args.args[0]],['package:curl','harness:codex'])

 def test_persistent_modes_unknown_items_and_incompatible_release_never_start(self):
  for choices in [{'package:curl':'persistent'},{'package:unknown':'session'},{'release:rescue':'session','package:curl':'session'}]:
   with patch.object(tasks,'session_update') as mutate:
    with self.assertRaises(ValueError):tasks.apply(self.items,choices)
    mutate.assert_not_called()

 def test_full_release_is_staged_in_ram_without_generation_activation(self):
  with patch.object(u,'release_update',return_value={'ok':True,'staged':True,'persistence_required':True}) as stage,patch.object(u,'activate') as activate:
   result=tasks.apply(self.items,{'release:rescue':'session'})
  self.assertTrue(result['ok']);stage.assert_called_once_with(expected_version='1.0.1',stage_ram=True);activate.assert_not_called()

 def test_failed_full_release_staging_never_activates_a_generation(self):
  with patch.object(u,'release_update',side_effect=ValueError('Fixture failure')),patch.object(u,'activate') as activate:
   result=tasks.apply(self.items,{'release:rescue':'session'})
  self.assertFalse(result['ok']);self.assertFalse(result['completed']);activate.assert_not_called()

 def test_select_all_ram_excludes_only_full_release(self):
  with patch('update_jobs.status',return_value=None),patch('update_jobs.cached_inventory',return_value=None):model=ui.Model()
  model.items=self.items;model.phase='list';model.select_all('session')
  self.assertEqual(model.choices['release:rescue'],'no')
  self.assertTrue(all(model.choices[r['id']]=='session' for r in self.items if r['kind']!='release'))
  model.select_all('persistent');self.assertNotIn('persistent',model.choices.values())
 def test_partial_temporary_failure_is_not_reported_as_success(self):
  with patch.object(tasks,'session_update',side_effect=ValueError('SYNTHETIC FAILURE')):
   result=tasks.apply(self.items,{'package:curl':'session'})
  self.assertFalse(result['ok']);self.assertEqual(result['completed'],[]);self.assertTrue(result['session_may_be_partial'])
 def test_ram_failure_never_falls_back_to_persistence(self):
  with patch.object(tasks,'session_update',side_effect=ValueError('No space')),patch.object(u,'package_generation') as persistent:
   result=tasks.apply(self.items,{'package:curl':'session'})
  self.assertFalse(result['ok']);self.assertFalse(result['completed']);persistent.assert_not_called()

 def test_shell_fragments_cannot_be_package_names_or_versions(self):
  for name,version in [('curl;id','1.1'),('curl','1.1\nBAD=yes'),('--root','1.0')]:
   with self.assertRaises(ValueError):tasks.rows({'packages':[{'name':name,'latest':version,'current':'1'}]})
 def test_ui_requires_check_selection_and_confirmation_without_auto_apply(self):
  import update_jobs
  with patch.object(update_jobs,'status',return_value=None),patch.object(update_jobs,'cached_inventory',return_value=None):m=ui.Model()
  m.inventory_result({'packages':[{'name':'curl','latest':'1.1','current':'1.0'}]})
  self.assertEqual(m.phase,'list');self.assertEqual(m.choices,{'package:curl':'no'});m.start('apply');self.assertIsNone(m.thread)
  m.cycle();self.assertEqual(m.choices['package:curl'],'session');m.cycle();self.assertEqual(m.choices['package:curl'],'no')
  m.phase='applying';self.assertFalse(m.back());m.job='a'*32;self.assertTrue(m.back());self.assertEqual(m.phase,'applying')
  m.accept({'operation':'apply','state':'done','result':{'ok':True,'results':[]}});self.assertEqual(m.phase,'done')
 def test_release_only_prepares_in_ram(self):
  m=ui.Model();m.phase='list';m.items=[next(row for row in self.items if row['kind']=='release')];m.choices={'release:rescue':'no'};m.cycle();self.assertEqual(m.choices['release:rescue'],'session');m.cycle();self.assertEqual(m.choices['release:rescue'],'no')
 def test_busy_model_ignores_second_submission_but_can_leave_progress(self):
  import threading,update_jobs
  entered=threading.Event();release=threading.Event()
  with patch.object(update_jobs,'status',return_value=None),patch.object(update_jobs,'cached_inventory',return_value=None):m=ui.Model()
  def slow(*args):entered.set();release.wait(2);return {'id':'a'*32,'operation':'check','state':'running'}
  with patch.object(update_jobs,'submit',side_effect=slow):
   m.start('check');self.assertTrue(entered.wait(1));m.start('check');self.assertEqual(m.phase,'checking');self.assertFalse(m.back());release.set();m.thread.join(2);m.drain()
  self.assertEqual(m.job,'a'*32);self.assertEqual(m.phase,'checking')
 def test_stream_progress_never_forwards_unknown_raw_process_text(self):
  events=[]
  with progress.listen(events.append):
   result=u.run([sys.executable,'-c',"print('SYNTHETIC-PRIVATE-TOKEN');print('pmstatus:curl:42:installing')"])
  self.assertIn(b'SYNTHETIC-PRIVATE-TOKEN',result.stdout);self.assertNotIn('SYNTHETIC-PRIVATE-TOKEN',json.dumps(events));self.assertEqual(events[-1]['completed'],42)
 def test_percent_requires_a_real_measurement_and_no_elapsed_time_guess(self):
  self.assertEqual(ui.measurement({'elapsed':20}), '');self.assertEqual(ui.measurement({'completed':42,'total':100,'unit':'apt'}),'APT 42%');self.assertEqual(ui.measurement({'completed':float('nan'),'total':100,'unit':'apt'}),'')

class PrivateGeneration(unittest.TestCase):
 def test_check_uses_ram_and_preserves_usb_contents_even_with_partial_sources(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);data=p/'data';data.mkdir();run=p/'run';run.mkdir();pin=p/'pin';pin.write_text('{}');(data/'owner-file').write_text('SYNTHETIC-OWNER')
   def one(names):return {names[0]:{'version':'1.1.0'}}
   with patch.object(u,'ROOT',data),patch.object(u,'NOTICE',run/'notice.json'),patch.object(u,'RUN',run),patch.object(u,'PIN',pin),patch.object(u,'state',return_value={'active':None}),patch.object(u,'running_generation',return_value=None),patch.object(u,'installed',return_value={n:'1.0.0' for n in u.BINS}),patch.object(u,'package_check',return_value=[]),patch.object(sources,'harnesses',side_effect=one),patch.object(sources,'catalog',side_effect=ValueError('offline')),patch.object(u,'atomic',side_effect=lambda path,value:path.write_text(json.dumps(value))):
    result=u.check()
   self.assertEqual(list(data.iterdir()),[data/'owner-file']);self.assertTrue((run/'checks.json').exists());self.assertIn('release',result['errors']);self.assertEqual(len(result['harnesses']),4)
 def test_pending_verified_generation_is_the_next_build_base_not_the_running_factory(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);g='gen-'+'b'*32;folder=p/g;(folder/'live').mkdir(parents=True);files={}
   for name in ['vmlinuz','initrd.img','filesystem.squashfs']:(folder/'live'/name).write_bytes(b'SYNTHETIC');files[name]=u.hashfile(folder/'live'/name)
   u.atomic(folder/'manifest.json',{'files':files})
   with patch.object(u,'ROOT',p),patch.object(u,'state',return_value={'active':g}):
    self.assertEqual(u.source_live(),folder/'live');(folder/'live/vmlinuz').write_bytes(b'CORRUPT')
    with self.assertRaises(ValueError):u.source_live()
 def test_carryover_only_contains_hash_verified_public_manager_files(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);src=p/'source';dest=p/'next';(src/'usr/share/aguja').mkdir(parents=True);record=src/'usr/share/aguja/update-runtime.json';files={}
   for name in u.PUBLIC_MANAGER_FILES:
    path=src/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('PUBLIC '+name).encode());path.chmod(0o644);files[name]=u.hashfile(path)
   record.write_text(json.dumps({'schema':1,'files':files}));record.chmod(0o644);secret=src/'home/aguja/private';secret.parent.mkdir(parents=True);secret.write_text('SYNTHETIC-SECRET')
   u.refresh_manager(dest,src);self.assertFalse((dest/'home').exists());self.assertEqual((dest/'usr/lib/aguja/updates.py').read_bytes(),(src/'usr/lib/aguja/updates.py').read_bytes())
   self.assertEqual((dest/'etc/initramfs-tools/hooks/aguja-update').stat().st_mode & 0o777,0o755)
   self.assertEqual((dest/'etc/systemd/system/aguja-update-job@.service').stat().st_mode & 0o777,0o644)
   (src/'usr/lib/aguja/updates.py').write_text('CHANGED')
   with self.assertRaises(ValueError):u.refresh_manager(p/'rejected',src)
   self.assertFalse((p/'rejected').exists())
 def test_session_guard_rejects_nonlive_and_disk_backed_overlay(self):
  with patch.object(Path,'read_text',return_value='boot=installed'):
   with self.assertRaises(ValueError):tasks.verify_live_ram()
  from subprocess import CompletedProcess
  root={'filesystems':[{'fstype':'overlay','options':'upperdir=/run/live/overlay/rw'}]};disk={'filesystems':[{'fstype':'ext4'}]}
  with patch.object(Path,'read_text',return_value='boot=live'),patch.object(u,'run',side_effect=[CompletedProcess([],0,json.dumps(root).encode()),CompletedProcess([],0,json.dumps(disk).encode())]):
   with self.assertRaises(ValueError):tasks.verify_live_ram()


class Elevation(unittest.TestCase):
 def test_direct_local_vt_without_tmux_flags_survives_sudo_pty(self):
  with patch.dict(os.environ,{},clear=True),patch.object(os,'ttyname',return_value='/dev/tty2'):
   self.assertIn('AGUJA_CONSOLE_TTY=/dev/tty2',u.elevated_command(['menu']))
  with patch.dict(os.environ,{'SSH_CONNECTION':'synthetic'},clear=True),patch.object(os,'ttyname',return_value='/dev/tty2'):
   self.assertNotIn('/usr/bin/env',u.elevated_command(['menu']))
 def test_only_valid_local_vt_context_survives_sudo_not_ssh_or_shell_text(self):
  with patch.dict(os.environ,{'AGUJA_LOCAL_CONSOLE':'1','AGUJA_CONSOLE_TTY':'/dev/tty1'},clear=True):
   command=u.elevated_command(['menu']);self.assertIn('AGUJA_CONSOLE_TTY=/dev/tty1',command)
  for env in [{'AGUJA_LOCAL_CONSOLE':'1','AGUJA_CONSOLE_TTY':'/dev/tty1;id'},{'AGUJA_LOCAL_CONSOLE':'1','AGUJA_CONSOLE_TTY':'/dev/tty1','SSH_CONNECTION':'synthetic'}]:
   with patch.dict(os.environ,env,clear=True):self.assertNotIn('/usr/bin/env',u.elevated_command(['menu']))

if __name__=='__main__':unittest.main()
