#!/usr/bin/python3
"""Local VT mouse reader: only pointer movement/buttons; never keyboard content."""
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import time

EVENT = struct.Struct('llHHi')
WORD_BITS = struct.calcsize('L')*8


def bitmap(text):
    return sum(int(word,16) << (index*WORD_BITS) for index,word in enumerate(reversed(text.split())))


def pointer_capable(ev, key, rel, absolute):
    return bool(ev & (1<<1) and key & (1<<272) and
                ((ev & (1<<2) and rel & 3 == 3) or (ev & (1<<3) and absolute & 3 == 3)))


class Motion:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.x, self.y = width//2, height//2

    def event(self, kind, code, value, ranges=None):
        action = None
        if kind == 2 and code in (0,1):
            if code==0:self.x+=value
            else:self.y+=value
            action='move'
        elif kind==3 and code in (0,1) and ranges and code in ranges:
            minimum,maximum=ranges[code]
            if maximum<=minimum:return None
            coordinate=round((value-minimum)/(maximum-minimum)*((self.width if code==0 else self.height)-1))
            if code==0:self.x=coordinate
            else:self.y=coordinate
            action='move'
        elif kind==2 and code==8 and value:
            action='wheel-up' if value>0 else 'wheel-down'
        elif kind==1 and code in (272,273) and value==1:
            action='click' if code==272 else 'back'
        self.x=max(0,min(self.width-1,self.x));self.y=max(0,min(self.height-1,self.y))
        return {'action':action,'x':self.x,'y':self.y} if action else None


def serve(width, height):
    devices={}
    for item in Path('/sys/class/input').glob('event[0-9]*'):
        fd=None
        if not item.name[5:].isdigit():continue
        caps=item/'device/capabilities'
        try:
            values=[bitmap((caps/name).read_text()) for name in ('ev','key','rel','abs')]
            if not pointer_capable(*values):continue
            fd=os.open('/dev/input/'+item.name,os.O_RDONLY|os.O_NONBLOCK|os.O_CLOEXEC)
            ranges={}
            if values[3]&3==3:
                for code in (0,1):
                    raw=fcntl.ioctl(fd,(2<<30)|(24<<16)|(ord('E')<<8)|(0x40+code),bytes(24))
                    _,minimum,maximum,_,_,_=struct.unpack('6i',raw)
                    ranges[code]=(minimum,maximum)
            devices[fd]=ranges
        except OSError:
            if fd is not None and fd not in devices:os.close(fd)
    # Open mouse handles first, then relinquish elevation permanently.
    if os.geteuid()==0 and os.environ.get('SUDO_UID','').isdigit():
        os.setgroups([]);os.setgid(int(os.environ['SUDO_GID']));os.setuid(int(os.environ['SUDO_UID']))
    motion=Motion(width,height)
    try:
        print(json.dumps({'action':'ready','devices':len(devices),'x':motion.x,'y':motion.y}),flush=True)
        while devices:
            ready,_,_=select.select(list(devices),[],[],1)
            for fd in ready:
                try:raw=os.read(fd,EVENT.size*32)
                except OSError:raw=b''
                if not raw:
                    os.close(fd);devices.pop(fd);continue
                for offset in range(0,len(raw)-EVENT.size+1,EVENT.size):
                    _,_,kind,code,value=EVENT.unpack_from(raw,offset)
                    update=motion.event(kind,code,value,devices[fd])
                    if update:print(json.dumps(update),flush=True)
    finally:
        for fd in devices:os.close(fd)


class Pointer:
    """Nonblocking UI client; helper lifespan is confined to the local panel."""
    def __init__(self,width,height):
        self.position=None
        self.pending=b''
        self.process=subprocess.Popen(['sudo','-n','/usr/bin/python3','/usr/lib/aguja/pointer.py',str(width),str(height)],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        os.set_blocking(self.process.stdout.fileno(),False)

    def poll(self):
        events=[]
        for _ in range(8):
            try:raw=os.read(self.process.stdout.fileno(),8192)
            except BlockingIOError:break
            if not raw:break
            self.pending+=raw
            if len(self.pending)>65536:self.pending=b'';break
        lines=self.pending.split(b'\n');self.pending=lines.pop()
        for line in lines:
            try:value=json.loads(line)
            except ValueError:continue
            if value.get('action')=='ready' and not value.get('devices'):continue
            if value.get('action') in ('ready','move','click','back','wheel-up','wheel-down'):
                self.position=(value['x'],value['y'])
                if value['action'] not in ('ready','move'):events.append(value)
        return events

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.process.stdout.close()


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit(2)
    width,height=map(int,sys.argv[1:])
    if not 320<=width<=4096 or not 240<=height<=2160:raise SystemExit(2)
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
    serve(width,height)
