"""Bounded per-CLI approval channel owned by the terminal relay, never a server."""
import json
import os
import select
import socket
import struct
import time
import activity
from i18n import t


class Broker:
    def __init__(self,directory):
        self.path=directory/'approve.sock'
        self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.listener.bind(str(self.path));self.path.chmod(0o600)
        self.listener.listen(8);self.listener.setblocking(False)

    def poll(self,write,input_fd=0):
        try:self._poll(write,input_fd)
        except (OSError,ValueError,TypeError,AttributeError):pass

    def _poll(self,write,input_fd=0):
        if not select.select([self.listener],[],[],0)[0]:return
        connection,_=self.listener.accept()
        with connection:
            _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=os.getuid():return
            connection.settimeout(1);raw=b''
            while b'\n' not in raw and len(raw)<=65536:
                part=connection.recv(4096)
                if not part:return
                raw+=part
            if len(raw)>65536:return
            try:request=json.loads(raw.split(b'\n',1)[0])
            except (ValueError,TypeError):return
            tool=str(request.get('tool_name','Task'))
            payload=request.get('tool_input',{})
            content=activity.redact(json.dumps(payload,ensure_ascii=False,indent=2),activity.secret_values(),command=True)
            # Flush already-queued accelerated Enter. Only a fresh affirmative
            # answer after the visible request can authorize this call.
            while select.select([input_fd],[],[],0)[0]:
                if not os.read(input_fd,4096):break
            write(('\r\n\x1b[0m'+t('Tarea pendiente de confirmación')+' · '+tool+'\r\n'+
                   content.replace('\n','\r\n')+'\r\n'+
                   t('Escribe sí / yes para ejecutar. Enter o Esc: cancelar.')+'\r\n> ').encode())
            answer=b'';deadline=time.monotonic()+570
            while time.monotonic()<deadline and len(answer)<32:
                if not select.select([input_fd],[],[],min(1,max(0,deadline-time.monotonic())))[0]:continue
                byte=os.read(input_fd,1)
                if byte in (b'',b'\x1b',b'\x03'):answer=b'';break
                if byte in (b'\r',b'\n'):break
                if byte in (b'\x7f',b'\x08'):
                    answer=answer[:-1];write(b'\b \b');continue
                answer+=byte;write(byte)
            approved=answer.decode('utf-8','replace').strip().casefold() in ('si','sí','yes','sim','oui','ja','sì','是')
            connection.sendall(b'approve\n' if approved else b'deny\n')
            write(('\r\n'+t('Confirmada' if approved else 'Cancelada')+'\r\n').encode())

    def close(self):
        self.listener.close();self.path.unlink(missing_ok=True)
