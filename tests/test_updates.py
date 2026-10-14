import importlib.util,json,tempfile,sys,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
import updates as u
class Generations(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name);self.data=self.p/'data';self.data.mkdir();self.cfg=self.p/'cfg';self.cfg.mkdir();self.root=self.data/'updates';self.root.mkdir()
  self.patches=[patch.object(u,'DATA',self.data),patch.object(u,'CFG',self.cfg),patch.object(u,'ROOT',self.root),patch.object(u,'STATE',self.root/'state.json')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in self.patches:p.stop()
  self.temp.cleanup()
 def test_activation_state_recovers_a_power_loss_after_boot_pointer_commit(self):
  new={'schema':1,'active':'gen-'+'a'*32,'previous':None};pointer=b'SYNTHETIC-BOOT-POINTER'
  original=u.atomic
  def fail(p,value):
   if p==u.STATE:raise SystemExit('power lost')
   original(p,value)
  with patch.object(u,'atomic',fail):
   with self.assertRaises(SystemExit):u.commit_state(new,pointer)
  self.assertEqual(u.state(),new);self.assertFalse((self.root/'pending-state.json').exists())
 def test_failed_pointer_commit_preserves_previous_state(self):
  old={'schema':1,'active':'gen-'+'b'*32,'previous':None};u.atomic(u.STATE,old);u.atomic(self.cfg/'aguja-update.cfg',b'OLD')
  original=u.atomic
  def fail(p,value):
   if p==self.cfg/'aguja-update.cfg':raise SystemExit('power lost')
   original(p,value)
  with patch.object(u,'atomic',fail):
   with self.assertRaises(SystemExit):u.commit_state({'schema':1,'active':'gen-'+'c'*32,'previous':old['active']},b'NEW')
  self.assertEqual(u.state(),old);self.assertEqual((self.cfg/'aguja-update.cfg').read_bytes(),b'OLD')
 def test_invalid_generation_paths_never_reach_boot_pointer(self):
  u.atomic(u.STATE,{'schema':1,'active':'../../private','previous':None})
  with self.assertRaises(ValueError):u.state()
 def test_nonpersistent_destination_refuses_mutation(self):
  with patch('os.path.ismount',return_value=False):
   with self.assertRaises(ValueError):u.capacity(1)
  self.assertEqual(list(self.root.iterdir()),[])
 def test_metadata_symlink_never_dumps_a_credential_file(self):
  secret=self.p/'private.json';secret.write_text(json.dumps({'tokens':{'access_token':'SYNTHETIC-SECRET'}}));(self.root/'state.json').symlink_to(secret)
  with self.assertRaises(ValueError):u.state()
 def test_unknown_state_fields_never_reach_status_output(self):
  u.atomic(u.STATE,{'schema':1,'active':None,'previous':None,'token':'SYNTHETIC-SECRET'})
  with self.assertRaises(ValueError):u.status()
 def test_downloaded_harness_must_report_the_verified_vendor_version(self):
  import subprocess
  with patch.object(u,'run',return_value=subprocess.CompletedProcess([],0,b'codex-cli 0.999.0',b'')):
   with self.assertRaises(ValueError):u.verify_harnesses(self.p,{'codex':{'version':'0.162.1'}})
  self.assertFalse((self.cfg/'aguja-update.cfg').exists())
 def test_factory_selection_keeps_a_verified_previous_boot_entry(self):
  g='gen-'+'d'*32;folder=self.root/g;(folder/'live').mkdir(parents=True)
  files={}
  for name in ('vmlinuz','initrd.img','filesystem.squashfs'):
   (folder/'live'/name).write_bytes(b'SYNTHETIC-BOOT');files[name]=u.hashfile(folder/'live'/name)
  u.atomic(folder/'manifest.json',{'schema':1,'files':files})
  reader=Path.read_text
  def read(path,*args,**kw):
   return '/dev/fixture5' if str(path)=='/run/aguja-data-device' else reader(path,*args,**kw)
  with patch.object(Path,'read_text',read),patch('subprocess.check_output',return_value='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'):
   pointer=u.boot_pointer({'schema':1,'active':None,'previous':g}).decode()
  self.assertIn('set default=aguja-factory',pointer);self.assertIn('--id aguja-previous',pointer);self.assertIn(g,pointer)
  (folder/'live/filesystem.squashfs').write_bytes(b'DAMAGED')
  pointer=u.boot_pointer({'schema':1,'active':None,'previous':g}).decode()
  self.assertIn('set default=aguja-factory',pointer);self.assertNotIn('--id aguja-previous',pointer)
  self.assertTrue((folder/'live/filesystem.squashfs').exists())
 def test_mutation_refuses_internal_boot_even_when_directories_are_mounted(self):
  def command(args,**kw):
   if args[0]=='findmnt':return '/dev/fixture3'
   if args[0]=='lsblk' and '--tree' not in args:return 'fixture'
   return json.dumps({'blockdevices':[{'type':'disk','path':'/dev/fixture','tran':'sata','rm':False}]})
  with patch.object(Path,'read_text',return_value='/dev/fixture5'),patch('subprocess.check_output',side_effect=command):
   with self.assertRaises(ValueError):u.verify_persistent_target()
  self.assertFalse((self.cfg/'aguja-update.cfg').exists())
 def test_mutation_refuses_data_mounted_from_another_disk(self):
  tree={'blockdevices':[{'type':'disk','path':'/dev/fixture','tran':'usb','rm':True,'children':[{'path':'/dev/fixture4','label':'AGUJA_CFG'},{'path':'/dev/fixture5','label':'AGUJA_DATA'}]}]}
  def command(args,**kw):
   if args[0]=='findmnt':return {'/run/live/medium':'/dev/fixture3','/config':'/dev/fixture4','/data':'/dev/other5'}[args[-1]]
   if args[0]=='lsblk' and '--tree' not in args:return 'fixture'
   return json.dumps(tree)
  with patch.object(Path,'read_text',return_value='/dev/fixture5'),patch('subprocess.check_output',side_effect=command):
   with self.assertRaises(ValueError):u.verify_persistent_target()
  self.assertFalse((self.cfg/'aguja-update.cfg').exists())
 def test_first_boot_guid_uses_synced_gpt_when_kernel_metadata_is_stale(self):
  guid='12345678-1234-1234-1234-123456789abc'
  with patch.object(Path,'read_text',return_value='5'),patch('subprocess.check_output',side_effect=['','fixture','Partition unique GUID: '+guid.upper()]):
   self.assertEqual(u.data_partuuid('/dev/fixture5'),guid)
 def test_invalid_gpt_identity_is_refused_without_activation(self):
  with patch.object(Path,'read_text',return_value='5'),patch('subprocess.check_output',side_effect=['','fixture','Partition info unavailable']):
   with self.assertRaises(ValueError):u.data_partuuid('/dev/fixture5')
  self.assertFalse((self.cfg/'aguja-update.cfg').exists())
if __name__=='__main__':unittest.main()
