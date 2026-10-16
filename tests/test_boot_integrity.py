import hashlib, os, subprocess, tempfile, unittest
from pathlib import Path
GUARD = Path(__file__).resolve().parents[1] / 'runtime/live-update-guard.sh'
class BootIntegrity(unittest.TestCase):
 def run_guard(self, mode=None, damaged=False, generation=None):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); bindir=root/'bin'; bindir.mkdir();gen=generation or 'gen-'+'a'*32
   media='/updates/'+gen+'/live';live=root/media.lstrip('/');live.mkdir(parents=True)
   original=b'synthetic root image';(live/'filesystem.squashfs').write_bytes(b'corrupt' if damaged else original)
   cmdline='aguja.generation='+gen+' aguja.sha256='+hashlib.sha256(original).hexdigest()
   if mode is not None:cmdline+=' aguja.verify='+mode
   (bindir/'cat').write_text('#!/bin/sh\nif [ "$1" = /proc/cmdline ]; then printf "%s\\n" "$TEST_CMDLINE"; else exec /bin/cat "$@"; fi\n');(bindir/'cat').chmod(0o755)
   (bindir/'sha256sum').write_text('#!/bin/sh\ntouch "$HASH_CALLED"\nexec /usr/bin/sha256sum "$@"\n');(bindir/'sha256sum').chmod(0o755)
   env={**os.environ,'PATH':str(bindir)+':'+os.environ['PATH'],'TEST_CMDLINE':cmdline,'HASH_CALLED':str(root/'hashed'),'LIVE_MEDIA_PATH':media}
   result=subprocess.run(['/bin/sh','-c','panic() { echo "$*" >&2; exit 7; }; . "$1"; aguja_verify_generation "$2"','test',str(GUARD),str(root)],env=env,capture_output=True,text=True)
   return result.returncode,(root/'hashed').exists()
 def test_normal_boot_does_not_read_complete_root(self):self.assertEqual(self.run_guard(),(0,False))
 def test_quick_mode_is_not_a_full_integrity_claim(self):self.assertEqual(self.run_guard('quick',damaged=True),(0,False))
 def test_full_diagnostic_accepts_valid_root(self):self.assertEqual(self.run_guard('full'),(0,True))
 def test_full_diagnostic_rejects_changed_root(self):self.assertEqual(self.run_guard('full',damaged=True),(7,True))
 def test_invalid_modes_and_generation_do_not_bypass_validation(self):
  self.assertEqual(self.run_guard('invalid'),(7,False));self.assertEqual(self.run_guard(generation='gen-invalid'),(7,False))
if __name__=='__main__':unittest.main()
