import json,os,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import update_jobs as jobs,update_ui as ui,updates,update_tasks
class BackgroundJobs(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  for key,path in {'ROOT':self.p/'jobs','ACTIVE':self.p/'jobs/active.json','PUBLIC':self.p/'public.json'}.items():
   p=patch.object(jobs,key,path);p.start();self.addCleanup(p.stop)
  p=patch.object(jobs.subprocess,'run',return_value=type('Result',(),{'returncode':0,'stdout':'active'})());self.systemd=p.start();self.addCleanup(p.stop)
  p=patch.object(jobs,'cached_inventory',return_value=None);p.start();self.addCleanup(p.stop)
 def test_submit_detaches_to_systemd_and_closing_ui_does_not_cancel_work(self):
  record=jobs.submit('check');self.assertIn('--no-block',self.systemd.call_args.args[0]);self.assertIn('aguja-update-job@'+record['id']+'.service',self.systemd.call_args.args[0])
  model=ui.Model();self.assertTrue(model.busy);self.assertTrue(model.back())
  with patch.object(updates,'check',return_value={'packages':[{'name':'curl','current':'1','latest':'2'}],'harnesses':{},'release':None}):self.assertEqual(jobs.worker(record['id']),0)
  reopened=ui.Model();self.assertEqual(reopened.phase,'list');self.assertEqual(reopened.items[0]['name'],'curl')
 def test_only_one_job_runs_and_a_second_apply_does_not_install(self):
  jobs.submit('check')
  items=[{'id':'package:curl','kind':'package','name':'curl','current':'1','latest':'2'}]
  with self.assertRaises(ValueError):jobs.submit('apply',items,{'package:curl':'persistent'})
  self.assertEqual(self.systemd.call_count,1)
 def test_apply_survives_reopening_and_preserves_verified_reboot_receipt(self):
  items=[{'id':'package:curl','kind':'package','name':'curl','current':'1','latest':'2'}];choices={'package:curl':'persistent'}
  record=jobs.submit('apply',items,choices)
  with patch.object(update_tasks,'apply',return_value={'ok':True,'completed':['package:curl'],'reboot_required':True}) as apply:self.assertEqual(jobs.worker(record['id']),0)
  apply.assert_called_once_with(items,choices);snapshot=json.loads(jobs.PUBLIC.read_text());self.assertTrue(snapshot['reboot_required']);self.assertEqual(ui.Model().phase,'done')
 def test_raw_exception_and_plan_are_not_published(self):
  record=jobs.submit('check')
  with patch.object(updates,'check',side_effect=RuntimeError('SYNTHETIC-PRIVATE-TOKEN')):self.assertEqual(jobs.worker(record['id']),1)
  self.assertNotIn('SYNTHETIC-PRIVATE-TOKEN',jobs.PUBLIC.read_text());self.assertNotIn('SYNTHETIC-PRIVATE-TOKEN',json.dumps(jobs.status()))
 def test_unit_finalizer_publishes_interruption_if_worker_was_killed(self):
  record=jobs.submit('check');jobs.finalize(record['id']);self.assertEqual(jobs.status()['state'],'failed');self.assertFalse(json.loads(jobs.PUBLIC.read_text())['ok'])
 def test_invalid_job_id_and_public_metadata_in_private_folder_are_refused(self):
  with self.assertRaises(ValueError):jobs.worker('../escape')
  jobs.submit('check');jobs.ACTIVE.chmod(0o644)
  with self.assertRaises(ValueError):jobs.status()
if __name__=='__main__':unittest.main()
