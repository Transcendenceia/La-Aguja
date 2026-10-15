"""Structured update progress: measured work only, no raw process output/secrets."""
import contextlib,re,threading,time
_state=threading.local()
@contextlib.contextmanager
def listen(callback):
 old=getattr(_state,'callback',None);_state.callback=callback
 try:yield
 finally:_state.callback=old
def active():return getattr(_state,'callback',None) is not None
def emit(stage,detail='',**values):
 callback=getattr(_state,'callback',None)
 if callback:callback({'stage':stage,'detail':str(detail)[:300],'time':time.monotonic(),**values})
def apt_line(line):
 # APT Status-Fd is a machine protocol. Package names and percentages only;
 # never forward URLs, maintainer-script text, environments or credentials.
 m=re.match(r'(?:pmstatus|dlstatus):([^:]*):([0-9.]+):',line)
 if m:
  percent=float(m[2]);name=m[1]
  if 0<=percent<=100 and (not name or re.fullmatch(r'[a-zA-Z0-9+._-]+(?::[a-z0-9-]+)?',name)):
   emit('install',name,completed=percent,total=100,unit='apt')
