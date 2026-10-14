import base64,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('usb_config',ROOT/'scripts/usb-config.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Transactions(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name)
  (self.p/'release.json').write_text(json.dumps({'features':['platform-profile-v1']}))
  self.old={n:('SYNTHETIC-ORIGINAL-'+n).encode() for n in c.FILES}
  for n,v in self.old.items():(self.p/n).write_bytes(v)
  (self.p/'unrelated').write_bytes(b'KEEP')
 def tearDown(self):self.temp.cleanup()
 def request(self):
  return {'operation':'write','snapshot':c.snapshot(self.p)[1],'files':{n:base64.b64encode(b'SYNTHETIC-NEW-'+n.encode()).decode() for n in c.FILES}}
 def test_edit_preserves_unrelated_files_and_exact_stored_backup(self):
  r=c.edit(self.p,self.request());self.assertTrue(r['verified']);self.assertEqual((self.p/'unrelated').read_bytes(),b'KEEP')
  for n,v in self.old.items():self.assertEqual((self.p/r['backup']/n).read_bytes(),v)
 def test_changed_snapshot_refuses_any_write(self):
  request=self.request();(self.p/c.FILES[0]).write_bytes(b'CONCURRENT');before={n:(self.p/n).read_bytes() for n in c.FILES}
  with self.assertRaises(ValueError):c.edit(self.p,request)
  self.assertEqual(before,{n:(self.p/n).read_bytes() for n in c.FILES});self.assertFalse(list(self.p.glob('aguja-config-backup-*')))
 def test_interrupted_multi_file_update_is_rolled_back_before_read(self):
  request=self.request();atomic=c.atomic
  def power_failure(p,v):
   if p.name==c.FILES[1] and p.parent==self.p:raise SystemExit('synthetic power loss')
   atomic(p,v)
  # Simulate abrupt termination beyond normal exception handling.
  with patch.object(c,'atomic',power_failure):
   with self.assertRaises(SystemExit):c.edit(self.p,request)
  c.recover(self.p)
  self.assertEqual(self.old,{n:(self.p/n).read_bytes() for n in c.FILES})
 def test_untrusted_journal_cannot_restore_outside_cfg(self):
  (self.p/'aguja-config-transaction.json').write_text(json.dumps({'backup':'../../outside','state':'prepared','original':{}}))
  with self.assertRaises(ValueError):c.recover(self.p)
 def test_runtime_recovery_matches_usb_helper_contract(self):
  source=(ROOT/'scripts/usb-config.py').read_text();self.assertEqual((ROOT/'runtime/config_transaction.py').read_text(),source[:source.index('def identify(')])
if __name__=='__main__':unittest.main()
