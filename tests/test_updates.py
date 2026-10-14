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
if __name__=='__main__':unittest.main()
