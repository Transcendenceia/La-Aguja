import base64,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import tailnet_identity as ti
import profile
class PortableIdentity(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  mapping={'CFG':'config','PRIVATE':'private','RUN':'run','SAVED':'config/aguja-tailnet-identity.json','STATE':'run/tailscaled.state','SETTINGS':'private/persistence.json','KEY':'private/persistence.key','STATUS':'status.json','RESTORED':'private/restored'}
  for key,name in mapping.items():
   p=patch.object(ti,key,self.p/name);p.start();self.addCleanup(p.stop)
  ti.CFG.mkdir();ti.RUN.mkdir()
  p=patch.object(ti,'target',return_value={'disk':'synthetic-usb'});self.target=p.start();self.addCleanup(p.stop)
  self.c={'tailscale':{'enabled':True,'login_server':'https://headscale.example.test','hostname':'portable-usb','auth_key':'SYNTHETIC-ENROLLMENT'}}
  self.state=b'{"_machinekey":"SYNTHETIC-MACHINE-IDENTITY","_profiles":{"x":1}}'
 def configure(self,encrypted=False):
  if encrypted:
   e={'protection':'encrypted','salt':profile.b64(b'0123456789abcdef')};password='synthetic-unlock'
  else:e={'protection':'plain'};password=None
  ti.configure(self.c,json.dumps(e).encode(),password)
 def native(self,raw=None):ti.write(ti.STATE,raw or self.state)
 def test_plain_identity_survives_new_hardware_without_another_enrollment(self):
  self.configure();self.native();self.assertTrue(ti.save());saved=ti.SAVED.read_bytes();ti.STATE.unlink()
  self.assertTrue(ti.restore());self.assertTrue(ti.restored());self.assertEqual(ti.STATE.read_bytes(),self.state);self.assertEqual(ti.SAVED.read_bytes(),saved)
  self.assertTrue(json.loads(ti.STATUS.read_text())['restored'])
 def test_encrypted_identity_requires_original_profile_unlock_and_never_spills_keys(self):
  self.configure(True);self.native();ti.save();sealed=ti.SAVED.read_bytes()
  self.assertNotIn(b'SYNTHETIC-MACHINE-IDENTITY',sealed);self.assertNotIn(ti.KEY.read_bytes(),sealed)
  ti.STATE.unlink();ti.KEY.unlink()
  with self.assertRaises(Exception):ti.restore()
  self.assertFalse(ti.STATE.exists());self.configure(True);self.assertTrue(ti.restore());self.assertEqual(ti.STATE.read_bytes(),self.state)
 def test_checkpoint_is_readback_verified_and_unchanged_state_never_rewrites_usb(self):
  self.configure();self.native();ti.save()
  with patch.object(ti,'write',wraps=ti.write) as write:
   ti.save();self.assertFalse(any(c.args[0]==ti.SAVED for c in write.call_args_list))
  self.assertEqual(json.loads(ti.STATUS.read_text())['state'],'saved')
 def test_failed_sync_keeps_previous_identity_and_does_not_claim_saved(self):
  self.configure();self.native();ti.save();before=ti.SAVED.read_bytes();self.native(b'{"_machinekey":"ROTATED"}')
  original=ti.write
  def fail(path,raw):
   if path==ti.SAVED:raise OSError('SYNTHETIC-SYNC-FAILURE')
   original(path,raw)
  with patch.object(ti,'write',side_effect=fail):self.assertEqual(ti.main(['save']),1)
  self.assertEqual(ti.SAVED.read_bytes(),before);self.assertEqual(json.loads(ti.STATUS.read_text())['state'],'error')
 def test_changed_tailnet_and_symlink_do_not_adopt_or_replace_a_saved_node(self):
  self.configure();self.native();ti.save();ti.STATE.unlink();self.c['tailscale']['login_server']='https://other.example.test';self.configure()
  with self.assertRaises(ValueError):ti.restore()
  self.assertFalse(ti.STATE.exists())
  victim=self.p/'victim';victim.write_text('owner');ti.STATE.symlink_to(victim)
  with self.assertRaises(ValueError):ti.save()
  self.assertEqual(victim.read_text(),'owner')
 def test_disabled_profile_does_not_unlock_or_delete_persisted_identity(self):
  self.configure(True);self.native();ti.save();before=ti.SAVED.read_bytes();ti.configure(None,b'{}')
  self.assertFalse(ti.SETTINGS.exists());self.assertFalse(ti.KEY.exists());self.assertEqual(ti.SAVED.read_bytes(),before)
 def test_new_authentication_marks_older_machine_key_checkpoint_pending_until_synced(self):
  self.configure();self.native();ti.save();before=ti.SAVED.read_bytes();self.native(b'{"_machinekey":"SYNTHETIC-MACHINE-IDENTITY","profile":"NEW-AUTH"}')
  with patch('subprocess.run'):ti.request_save()
  self.assertEqual(json.loads(ti.STATUS.read_text())['state'],'pending');self.assertEqual(ti.SAVED.read_bytes(),before)
  ti.save();self.assertEqual(json.loads(ti.STATUS.read_text())['state'],'saved');self.assertNotEqual(ti.SAVED.read_bytes(),before)
 def test_connected_service_requests_nonblocking_checkpoint(self):
  self.configure()
  with patch('subprocess.run') as run:ti.request_save()
  self.assertIn('--no-block',run.call_args.args[0]);self.assertNotIn('SYNTHETIC',str(run.call_args))
if __name__=='__main__':unittest.main()
