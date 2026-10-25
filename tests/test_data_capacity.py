import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import data_capacity as dc

class DataCapacityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.cfg=Path(self.tmp.name);self.marker=self.cfg/'data-initialize.json'
  self.marker.write_text(json.dumps({'schema':1,'state':'pending'}))
  (self.cfg/'release.json').write_text(json.dumps({'features':['persistent-updates-v1']}))
  self.doc={'path':'/dev/sdb','type':'disk','tran':'usb','rm':True,'size':12*1024**3,'children':[{'path':'/dev/sdb4','label':'AGUJA_CFG'},{'path':'/dev/sdb5','label':'AGUJA_DATA'}]}
  p=patch.object(dc,'STATUS',self.cfg/'runtime-status.json');p.start();self.addCleanup(p.stop)
 def output(self,argv,**kw):
  if argv[0]=='lsblk':return json.dumps({'blockdevices':[self.doc]}).encode()
  if argv[0]=='sgdisk':return 'First sector: 100000\nLast sector: 20000000\nPartition unique GUID: 12345678-1234-1234-1234-123456789ABC\n'
  if argv[0]=='losetup':return '/dev/loop77\n'
  raise AssertionError(argv)
 def test_fixed_scsi_boot_continues_without_partition_mutation_and_keeps_pending_marker(self):
  self.doc.update(tran=None,rm=False)
  with patch.object(dc.subprocess,'check_output',side_effect=self.output) as observed,patch.object(dc.subprocess,'run') as mutate:
   self.assertIsNone(dc.initialize(self.cfg,'/dev/sdb','/dev/sdb5'))
  mutate.assert_not_called();self.assertEqual(observed.call_count,1)
  self.assertEqual(json.loads(self.marker.read_text())['state'],'pending')
  status=json.loads(dc.STATUS.read_text());self.assertEqual(status['state'],'deferred');self.assertFalse(status['disk_modified'])
 def test_nonremovable_usb_is_not_a_reason_to_repartition(self):
  self.doc['rm']=False
  with patch.object(dc.subprocess,'check_output',side_effect=self.output),patch.object(dc.subprocess,'run') as mutate:
   self.assertIsNone(dc.initialize(self.cfg,'/dev/sdb','/dev/sdb5'))
  mutate.assert_not_called()
 def test_complete_media_skips_all_initialization(self):
  self.marker.write_text('{"state":"complete"}')
  with patch.object(dc.subprocess,'check_output') as observed,patch.object(dc.subprocess,'run') as mutate:
   self.assertIsNone(dc.initialize(self.cfg,'/dev/sdb','/dev/sdb5'))
  observed.assert_not_called();mutate.assert_not_called()
 def test_wrong_disk_is_not_treated_as_an_ordinary_vm_bus_mismatch(self):
  self.doc.update(path='/dev/other',tran=None,rm=False)
  with patch.object(dc.subprocess,'check_output',side_effect=self.output),patch.object(dc.subprocess,'run') as mutate:
   with self.assertRaises(ValueError):dc.initialize(self.cfg,'/dev/sdb','/dev/sdb5')
  mutate.assert_not_called();self.assertFalse(dc.STATUS.exists())
 def test_usb_initialization_preserves_guid_and_completes_only_after_filesystem_success(self):
  read_text=Path.read_text
  def read(p,*a,**k):
   return ('5' if p.name=='partition' and p.parent.name=='sdb5' else '4') if str(p).startswith('/sys/class/block/') else read_text(p,*a,**k)
  with patch.object(dc.subprocess,'check_output',side_effect=self.output),patch.object(dc.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as mutate,patch.object(Path,'read_text',read):
   self.assertEqual(dc.initialize(self.cfg,'/dev/sdb','/dev/sdb5'),'/dev/loop77')
  self.assertEqual(json.loads(self.marker.read_text())['state'],'complete')
  self.assertTrue(any('-u' in c.args[0] and '5:12345678-1234-1234-1234-123456789ABC' in c.args[0] for c in mutate.call_args_list))
  self.assertEqual(mutate.call_args_list[-1].args[0],['resize2fs','/dev/loop77'])
if __name__=='__main__':unittest.main()
