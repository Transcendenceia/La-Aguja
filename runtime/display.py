"""Pixel cockpit for a local Linux VT; Pillow is optional for terminal fallback.

Only supported, currently-visible true-colour framebuffers are written. This module
never opens a browser, changes a video mode, or needs to run as root.
"""
import ctypes
import fcntl
from functools import lru_cache
import math
import os
from pathlib import Path
import re
import time
from i18n import result_text, event_text, t, ui_language

BG = '#08121b'
CARD = '#101f2b'
EDGE = '#233d4c'
CYAN = '#67e8db'
GOLD = '#ffd282'
WHITE = '#edf5f6'
DIM = '#9ab0bc'
GREEN = '#8cdeae'
RED = '#ff969a'
ANSI = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))')


def clean(text):
    """Do not let peer output draw controls or override UI labels."""
    text = ANSI.sub('', str(text))
    return ''.join(c if c == '\n' or (c.isprintable() and c not in '\u202a\u202b\u202d\u202e\u202c\u2066\u2067\u2068\u2069') else ' ' for c in text)


def layout(width, height):
    if width < 320 or height < 240:
        raise ValueError('Framebuffer too small for a readable cockpit')
    scale = max(.65, min(width / 1280, height / 720, 1.65))
    margin = max(12, round(26 * scale))
    header = round(128 * scale)
    footer = round(70 * scale)
    body = (margin, header, width - margin, height - footer)
    sidebar = round(min(340 * scale, width * .30)) if width >= 900 else 0
    return {'scale': scale, 'margin': margin, 'header': header, 'footer': footer,
            'stream': (margin, header, width - margin - sidebar - (margin if sidebar else 0), height - footer),
            'sidebar': (width - margin - sidebar, header, width - margin, height - footer) if sidebar else None,
            'body': body}


@lru_cache(maxsize=30)
def _font(size, bold=False, mono=False, language='es'):
    from PIL import ImageFont
    if language == 'zh':
        for candidate in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if bold else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',):
            try:
                return ImageFont.truetype(candidate, size, index=2)
            except OSError:
                pass
    family = 'DejaVuSansMono' if mono else 'DejaVuSans'
    name = family + ('-Bold' if bold else '') + '.ttf'
    for root in ('/usr/share/fonts/truetype/dejavu', '/usr/share/aguja/branding/fonts'):
        try:
            return ImageFont.truetype(str(Path(root) / name), size)
        except OSError:
            pass
    return ImageFont.load_default()


def font(size, bold=False, mono=False):
    return _font(size, bold, mono, ui_language())


def asset_root():
    installed = Path('/usr/share/aguja/branding')
    return installed if installed.exists() else Path(__file__).resolve().parent.parent / 'branding'


@lru_cache(maxsize=80)
def mascot(expression, size, root):
    from PIL import Image
    base = Path(root)
    for path in (base / 'mascot' / (expression + '.png'), base / (expression + '.png'),
                 base / 'aguja-mascot.png', base / 'mascot' / 'aguja-mascot.png'):
        try:
            with Image.open(path) as image:
                image = image.convert('RGBA')
                box = image.getbbox()
                if box:
                    image = image.crop(box)
                image.thumbnail((size, size), Image.Resampling.LANCZOS)
                return image
        except OSError:
            pass
    return None


def expression_at(tick, busy=False, connected=False):
    phase = tick % 8
    if connected and phase < .8:
        return 'surprise'
    if busy:
        return 'look-left' if phase < 3 else ('mischief' if phase < 5 else 'look-right')
    if 1.1 < phase < 1.35 or 5.2 < phase < 5.45:
        return 'blink'
    return 'wink' if 6 < phase < 6.7 else 'idle'


def event_kind(event):
    return {"session_start": "connect", "session_end": "disconnect", "command_start": "command", "command_end": "result"}.get(event.get("kind"), event.get("kind", "output"))


def active_sessions(activity):
    return [s for s in activity.get("sessions", []) if s.get("status") not in ("ended", "disconnected")]


def event_rows(events):
    rows = []
    for event in events[-200:]:
        kind = event_kind(event)
        stamp = event.get('time', '')
        try:
            stamp = time.strftime('%H:%M:%S', time.localtime(float(stamp)))
        except (TypeError, ValueError, OverflowError):
            stamp = clean(stamp)[:8]
        prefix = {'command': '$ ', 'connect': '+ ', 'disconnect': '- ', 'error': '! '}.get(kind, '')
        for index, text in enumerate(clean(event_text(event)).splitlines() or ['']):
            rows.append((stamp if index == 0 else '', prefix + text if index == 0 else text, kind))
    return rows


def process_rows(processes):
    """Stable parent/child order; tolerate already-exited parents and cycles."""
    by_id = {p.get('pid'): p for p in processes[:160]}
    children = {}
    for p in by_id.values():
        children.setdefault(p.get('ppid'), []).append(p)
    rows, visited = [], set()
    def visit(p, depth):
        pid = p.get('pid')
        if pid in visited:
            return
        visited.add(pid)
        rows.append(('  ' * min(depth, 5) + ('↳ ' if depth else '') + str(pid) + '  ' + clean(p.get('command', '')), p.get('state', '')))
        for child in sorted(children.get(pid, []), key=lambda item: str(item.get('pid'))):
            visit(child, depth + 1)
    for p in by_id.values():
        if p.get('ppid') not in by_id:
            visit(p, 0)
    for p in by_id.values():
        visit(p, 0)
    return rows


class ResourceStats:
    def __init__(self):
        self.previous = None
        self.result = {'cpu': 0, 'ram': 0}

    def sample(self):
        try:
            nums = [int(n) for n in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
            now = (sum(nums), nums[3] + nums[4])
            if self.previous and now[0] > self.previous[0]:
                self.result['cpu'] = max(0, min(100, round(100 * (1 - (now[1] - self.previous[1]) / (now[0] - self.previous[0])))))
            self.previous = now
            mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
            self.result['ram'] = round(100 * (1 - mem.get('MemAvailable', 0) / mem['MemTotal']))
        except (OSError, ValueError, KeyError, ZeroDivisionError):
            pass
        return dict(self.result)


def command_geometry(width, height):
    geo=layout(width,height);s=geo['scale'];m=geo['margin']
    x0,y0,x1,y1=geo['stream']
    return (x0+m*.65,y0+round(73*s),x1-m*.65,y1-m*.65,round(110*s))


def pointer_action(control, snapshot, event, width, height):
    action=event.get('action')
    if action=='back':control.key('back',snapshot);return
    if action in ('wheel-up','wheel-down'):
        control.key('up' if action=='wheel-up' else 'down',snapshot);return
    if action!='click' or control.view!='commands':return
    x,y,right,bottom,cardheight=command_geometry(width,height)
    px,py=event['x'],event['y']
    if control.detail:
        if x<=px<=right and y<=py<y+cardheight*.25:control.key('back',snapshot)
        return
    if not x<=px<=right or not y<=py<bottom:return
    import panel_state
    commands=panel_state.command_window(control.data(snapshot).get('commands',[]),control.selected,max(1,int((bottom-y)/cardheight)))
    index=int((py-y)/cardheight)
    if 0<=index<len(commands):control.select(commands[index]['id'],expand=True)


def render(width, height, current, activity=None, tick=0, paused=False, scroll=0,
           view='activity', selected=0, countdown=0, stats=None, brand_root=None, release=None, control=None, pointer=None):
    """Pure render entrypoint for previews and framebuffer; no device side effects."""
    from PIL import Image, ImageDraw
    activity = activity or {}
    raw_activity = activity
    if control:
        activity = control.data(activity)
    stats = stats or {}
    release = t('desarrollo') if release is None else release
    sessions = active_sessions(activity)
    events = activity.get('events', [])
    processes = activity.get('processes', [])
    geo = layout(width, height)
    s, m = geo['scale'], geo['margin']
    image = Image.new('RGB', (width, height), BG)
    d = ImageDraw.Draw(image)
    title_font, text_font = font(round(28*s), True), font(round(17*s))
    mono = font(round(15*s), mono=True)
    small = font(round(13*s))
    lineheight = round(25*s)

    def text(x, y, value, color=WHITE, f=text_font, max_width=None):
        value = clean(value).replace('\n', ' ')
        if max_width is not None:
            if d.textlength(value, font=f) > max_width:
                lo,hi=0,len(value)
                while lo<hi:
                    mid=(lo+hi+1)//2
                    if d.textlength(value[:mid]+'…',font=f)<=max_width:lo=mid
                    else:hi=mid-1
                value=value[:lo]+'…' if lo else ''
        d.text((x, y), value, fill=color, font=f)

    def panel(box, title, note=''):
        d.rounded_rectangle(box, radius=round(15*s), fill=CARD, outline=EDGE, width=1)
        x0,y0,x1,y1 = box
        text(x0+m*.65, y0+16*s, title, CYAN, font(round(13*s),True), x1-x0-m)
        if note:
            text(x0+m*.65, y0+39*s, note, DIM, small, x1-x0-m)
        return x0+m*.65,y0+round(73*s),x1-m*.65,y1-m*.65

    text(m, m*.6, t('LA AGUJA RESCUE DISK'), CYAN, title_font, width-m*2)
    text(m, 53*s, t('Una entrada pequeña. Control completo.'), DIM, small)
    ip = current.get('addresses', [{}])[0].get('ip', '') if current.get('addresses') else ''
    if ip:
        port = current.get('ssh_port',22)
        cmd = 'ssh' + (f' -p {port}' if str(port) != '22' else '') + ' aguja@' + ip
        text(m, 82*s, cmd, GOLD, mono, width-m*2)
    else:
        message = t('Sin red · asistente Wi-Fi en {countdown}s', countdown=countdown) if countdown else t('Sin red · pulsa W para conectar Wi-Fi o conecta Ethernet')
        text(m, 82*s, message, GOLD, mono, width-m*2)
    if width >= 900:
        right = width - m - 310*s
        text(right, m, t('SSH LISTO') if current.get('ssh_active') else t('SSH INICIANDO'), CYAN, small)
        text(right, 51*s, t('{count} sesión(es)  ·  CPU {cpu}%  ·  RAM {ram}%', count=len(sessions), cpu=stats.get('cpu',0), ram=stats.get('ram',0)), DIM, small)
        for idx,key in enumerate(('cpu','ram')):
            gx = right+idx*145*s
            d.rounded_rectangle((gx,74*s,gx+120*s,77*s),radius=1,fill=EDGE)
            d.rounded_rectangle((gx,74*s,gx+120*s*max(0,min(100,stats.get(key,0)))/100,77*s),radius=1,fill=CYAN if key=='cpu' else GOLD)
        text(right, 87*s, current.get('mdns') or t('mDNS esperando'), DIM, small)

    if not geo['sidebar']:
        pose = expression_at(tick,bool(processes),False)
        sprite = mascot(pose,max(32,round(80*s)),str(brand_root or asset_root()))
        if sprite:
            image.paste(sprite,(width-m-sprite.width,round(12*s+math.sin(tick*2.3)*2*s)),sprite)

    stream = geo['stream']
    heading = {'commands':t('TAREAS Y COMANDOS'), 'activity':t('TERMINAL REMOTA · EN DIRECTO'), 'processes':t('ÁRBOL DE PROCESOS'), 'help':t('CENTRO DE RESCATE')}.get(view,t('TERMINAL REMOTA'))
    state = t('PAUSADA · L vuelve al directo') if paused else t('En directo · ↑↓ selecciona · Enter abre el detalle')
    if control:
        state += (t(' · Solo fallos') if control.failures else '') + (t(' · Una sesión') if control.session else '')
        if activity.get('technical_count'):
            state += f" · {activity['technical_count']} sondeos técnicos {t('visibles') if control.technical else t('agrupados (B)')}"
    x,y,right,bottom = panel(stream, heading, state)
    row_capacity = max(1, int((bottom-y) / lineheight))
    if view == 'commands':
        import panel_state
        commands = activity.get('commands', [])
        chosen = control.selected_command(activity) if control else commands[-1] if commands else None
        now = raw_activity.get('updated', time.time()) if paused else time.time()
        colors = {'running':CYAN,'ok':GREEN,'error':RED,'cancelled':GOLD,'probe':DIM,'disconnected':GOLD}
        labels = {'running':t('EN CURSO'),'ok':t('COMPLETADO'),'error':t('FALLO'),'cancelled':t('INTERRUMPIDO'),'probe':t('SONDEO GIT'),'disconnected':t('SIN RESULTADO')}
        if chosen and control and control.detail:
            text(x,y,t('Esc / clic derecho: plegar · ←→ otro comando · ↑↓ / rueda: desplazar'),GOLD,small,right-x)
            lines = [chosen.get('title',t('Comando')),chosen.get('command',''),
                     labels.get(chosen.get('status'),t('FINALIZADO'))+' · '+panel_state.command_duration(chosen,now)+' · '+result_text(chosen.get('result',t('En ejecución'))),
                     'ID: '+chosen.get('id','')+' · '+chosen.get('transport','ssh'),
                     time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(chosen.get('started',now))),
                     t('Salida privada: disponible por SSH, no se muestra aquí.') if chosen.get('output_private') else t('Salida filtrada del comando:')]
            lines += [e.get('text','') for e in events if e.get('kind')=='output' and e.get('command_id')==chosen.get('id')]
            chars=max(12,int((right-x)/max(1,d.textlength('M',font=mono))))
            wrapped=panel_state.wrap_lines(lines,chars)
            capacity=max(1,row_capacity-2)
            control.bound_scroll(len(wrapped),capacity)
            scroll=control.scroll
            text(x,y+lineheight,f'{scroll+1}–{min(len(wrapped),scroll+capacity)} / {len(wrapped)}',DIM,small,right-x)
            for i,line in enumerate(wrapped[scroll:scroll+capacity]):text(x,y+(i+2)*lineheight,line,WHITE,mono,right-x)
        else:
            cardheight=round(110*s)
            capacity=max(1,int((bottom-y)/cardheight))
            for i,c in enumerate(panel_state.command_window(commands,chosen.get('id') if chosen else None,capacity)):
                yy=y+i*cardheight
                focused=chosen and c.get('id')==chosen.get('id')
                color=colors.get(c.get('status'),DIM)
                d.rounded_rectangle((x-7*s,yy-4*s,right,yy+cardheight-12*s),radius=7*s,
                                    fill='#18333d' if focused else BG,outline=GOLD if focused else EDGE)
                stamp=time.strftime('%H:%M:%S',time.localtime(c.get('started',now)))
                indicator='◐◓◑◒'[int(tick*4)%4]+' ' if c.get('status')=='running' and not paused else ''
                text(x+7*s,yy,indicator+labels.get(c.get('status'),t('FINALIZADO'))+' · '+panel_state.command_duration(c,now)+' · '+stamp,color,small,right-x-14*s)
                text(x+7*s,yy+25*s,c.get('title',c.get('command','')),WHITE,mono,right-x-14*s)
                text(x+7*s,yy+50*s,c.get('command','').replace('\n',' ↵ '),WHITE,mono,right-x-14*s)
                text(x+7*s,yy+75*s,(result_text(c.get('result')) or t('En ejecución'))+' · '+t('Enter / clic: desplegar'),DIM,small,right-x-14*s)
        if not commands:
            text(x,y,t('Lista para trabajar · esperando una tarea remota.'),WHITE,mono,right-x)
            text(x,y+2*lineheight,t('aguja run --label "Revisar memoria" -- free -h'),CYAN,mono,right-x)
            text(x,y+3*lineheight,t('S cambia sesión · F filtra fallos · B muestra sondeos'),DIM,small,right-x)
    elif view == 'help':
        choices = [t('1  Consola Zsh'), t('2  Conectar Wi-Fi'), t('3  Guía y herramientas'), t('8  Diagnóstico'), '4  Codex', '5  Antigravity', '6  Claude Code', '7  OpenCode', t('9  Contraseña SSH'), t('R  Tailscale / Headscale · SSH privado')]
        for i, label in enumerate(choices[:row_capacity]):
            text(x, y+i*lineheight, ('› ' if i==selected else '  ')+label, GOLD if i==selected else WHITE, mono, right-x)
    elif view == 'processes':
        for i, (label,state) in enumerate(process_rows(processes)[scroll:scroll+row_capacity]):
            text(x,y+i*lineheight,label + '  ['+clean(state)+']',WHITE,mono,right-x)
        if not processes:
            text(x,y,t('Sin procesos remotos activos.'),DIM,mono,right-x)
    else:
        rows = event_rows(events)
        # Wrap long command/output lines instead of silently truncating them.
        wrapped = []
        chars = max(12, int((right-x-90*s) / max(1,d.textlength('M',font=mono))))
        for stamp, label, kind in rows:
            chunks = [label[i:i+chars] for i in range(0,len(label),chars)] or ['']
            wrapped.extend((stamp if i==0 else '',chunk,kind) for i,chunk in enumerate(chunks))
        end = max(0,len(wrapped)-scroll)
        for i,(stamp,label,kind) in enumerate(wrapped[max(0,end-row_capacity):end]):
            yy = y+i*lineheight
            if kind in ('connect','disconnect'):
                d.rounded_rectangle((x-5,yy-2,right,yy+lineheight-2),radius=4,fill='#193f43' if kind=='connect' else '#3d3026')
            text(x,yy,stamp,DIM,small,80*s)
            text(x+90*s,yy,label,GOLD if kind=='command' else CYAN if kind=='connect' else WHITE,mono,right-x-90*s)
        if not wrapped:
            text(x,y,t('Esperando una conexión SSH…') if activity.get('available',True) else t('Observador no disponible · aguja doctor'),WHITE,mono,right-x)
            text(x,y+lineheight*2,t('Aquí verás comandos, resultados y procesos en vivo.'),DIM,text_font,right-x)
            text(x,y+lineheight*3,t('El equipo está listo. No se modifican discos al observar.'),DIM,small,right-x)
    sidebar = geo['sidebar']
    if sidebar:
        sx,sy,sr,sb = panel(sidebar,t('SESIONES Y PROCESOS'),t('{count} conexión(es) activas', count=len(sessions)))
        mascot_space = round(150*s)
        limit = sb-mascot_space
        for session in sessions[:3]:
            if sy+lineheight*2>limit:
                break
            text(sx,sy,session.get('user','aguja')+' @ '+str(session.get('peer','')),CYAN,small,sr-sx)
            sy += lineheight
            text(sx,sy,session.get('command') or session.get('status',t('conectada')),DIM,mono,sr-sx)
            sy += lineheight+10*s
        if sy+lineheight*2<limit:
            text(sx,sy,t('PROCESOS'),DIM,font(round(11*s),True),sr-sx)
            sy += lineheight
            for label,state in process_rows(processes):
                if sy+lineheight>limit:
                    break
                text(sx,sy,label,WHITE,small,sr-sx)
                sy+=lineheight
        connection_recent = any(event_kind(e)=='connect' and isinstance(e.get('time'),(float,int)) and time.time()-e['time'] < 5 for e in events[-3:])
        pose = expression_at(tick,bool(processes),connection_recent)
        sprite = mascot(pose,round(145*s),str(brand_root or asset_root()))
        if sprite:
            mx = round(sr-sprite.width-8*s+math.sin(tick*1.3)*5*s)
            my = round(sb-sprite.height-15*s+math.sin(tick*2.3)*3*s)
            image.paste(sprite,(mx,my),sprite)
        text(sx,sb-40*s,'AGUJITA',CYAN,font(round(11*s),True),100*s)
        text(sx,sb-23*s,t('Trabajando') if processes else t('Lista para ayudar'),DIM,small,125*s)
    # Connect/disconnect notification remains visible for five seconds.
    recent = next((e for e in reversed(events) if event_kind(e) in ('connect','disconnect') and isinstance(e.get('time'),(float,int)) and 0<=time.time()-e['time']<5),None)
    if recent:
        tw = min(width-m*2,round(510*s))
        tx = (width-tw)//2
        ty = geo['header']+10*s
        d.rounded_rectangle((tx,ty,tx+tw,ty+55*s),radius=12,fill='#24545a',outline=CYAN,width=2)
        text(tx+16*s,ty+17*s,event_text(recent),WHITE,small,tw-32*s)
    fy = height-geo['footer']+14*s
    text(m,fy,t('↑↓ Elegir / desplazar · Enter / clic Desplegar · Esc Plegar · PgUp/PgDn · S Sesión · F Fallos · B Sondeos · L Directo · Tab Vistas · Q Consola'),WHITE,small,width-2*m)
    mode = current.get('ssh_auth_mode')
    credential = t('Usuario / contraseña de fábrica: aguja') if mode=='default' else t('Acceso SSH: clave pública') if mode=='key' else t('Contraseña personalizada · no se muestra')
    text(m,fy+25*s,credential+'   ·   '+release+t('   ·   Comandos y argumentos visibles; secretos ocultos'),DIM,font(round(11*s)),width-m*2)
    if pointer:
        px,py=pointer
        d.polygon([(px,py),(px,py+16),(px+5,py+12),(px+10,py+20),(px+13,py+18),(px+8,py+10),(px+16,py+10)],fill=WHITE,outline=BG)
    return image


class BitField(ctypes.Structure):
    _fields_ = [('offset',ctypes.c_uint32),('length',ctypes.c_uint32),('msb_right',ctypes.c_uint32)]


class VarInfo(ctypes.Structure):
    _fields_ = [(name,ctypes.c_uint32) for name in ('xres','yres','xres_virtual','yres_virtual','xoffset','yoffset','bits_per_pixel','grayscale')] + [('red',BitField),('green',BitField),('blue',BitField),('transp',BitField)] + [(name,ctypes.c_uint32) for name in ('nonstd','activate','height','width','accel_flags','pixclock','left_margin','right_margin','upper_margin','lower_margin','hsync_len','vsync_len','sync','vmode','rotate','colorspace')] + [('reserved',ctypes.c_uint32*4)]


class FixInfo(ctypes.Structure):
    _fields_ = [('id',ctypes.c_char*16),('smem_start',ctypes.c_ulong),('smem_len',ctypes.c_uint32),('type',ctypes.c_uint32),('type_aux',ctypes.c_uint32),('visual',ctypes.c_uint32),('xpanstep',ctypes.c_uint16),('ypanstep',ctypes.c_uint16),('ywrapstep',ctypes.c_uint16),('line_length',ctypes.c_uint32),('mmio_start',ctypes.c_ulong),('mmio_len',ctypes.c_uint32),('accel',ctypes.c_uint32),('capabilities',ctypes.c_uint16),('reserved',ctypes.c_uint16*2)]


def pixel_format(var, fix):
    """Reject anything except standard RGB/BGR packed true-colour safely."""
    bpp = var.bits_per_pixel
    if bpp not in (24,32) or fix.type!=0 or fix.visual!=2 or var.grayscale or var.nonstd:
        raise ValueError('Unsupported framebuffer format')
    if any(c.length!=8 or c.msb_right for c in (var.red,var.green,var.blue)) or var.green.offset!=8:
        raise ValueError('Unsupported channel format')
    order = (var.red.offset,var.blue.offset)
    if order not in ((16,0),(0,16)):
        raise ValueError('Unsupported RGB layout')
    width,height = var.xres,var.yres
    if not 320<=width<=4096 or not 240<=height<=2160:
        raise ValueError('Unsupported framebuffer size')
    bytespp=bpp//8
    if var.xoffset+width>var.xres_virtual or var.yoffset+height>var.yres_virtual or fix.line_length<(var.xoffset+width)*bytespp:
        raise ValueError('Invalid framebuffer pitch')
    end=(var.yoffset+height-1)*fix.line_length+(var.xoffset+width)*bytespp
    if end>fix.smem_len or fix.smem_len>256*1024*1024:
        raise ValueError('Invalid framebuffer memory size')
    if var.transp.length and (bpp!=32 or var.transp.length!=8 or var.transp.offset!=24 or var.transp.msb_right):
        raise ValueError('Unsupported transparency layout')
    suffix = ('A' if var.transp.length else 'X') if bpp==32 else ''
    return ('BGR' if order==(16,0) else 'RGB')+suffix


class Framebuffer:
    def __init__(self,tty_fd=0,device='/dev/fb0'):
        self.fd=None
        self.graphics=False
        self.tty_fd=tty_fd
        tty=os.ttyname(tty_fd)
        if not re.fullmatch(r'/dev/tty[1-9][0-9]*',tty):
            raise OSError('Not a local VT')
        if Path('/sys/class/tty/tty0/active').read_text().strip()!=Path(tty).name:
            raise OSError('Not the visible VT')
        try:
            self.fd=os.open(device,os.O_RDWR)
            self.var=VarInfo()
            self.fix=FixInfo()
            fcntl.ioctl(self.fd,0x4600,self.var)
            fcntl.ioctl(self.fd,0x4602,self.fix)
            self.raw_mode=pixel_format(self.var,self.fix)
            self.width,self.height=self.var.xres,self.var.yres
            fcntl.ioctl(self.tty_fd,0x4B3A,1)  # KDSETMODE / KD_GRAPHICS
            self.graphics=True
        except BaseException:
            self.close()
            raise

    def present(self,image):
        if image.size!=(self.width,self.height):
            raise ValueError('Frame size does not match mapped device')
        data=image.convert('RGBA' if self.raw_mode.endswith('A') else 'RGB').tobytes('raw',self.raw_mode)
        rowlen=self.width*(self.var.bits_per_pixel//8)
        offset=self.var.yoffset*self.fix.line_length+self.var.xoffset*(self.var.bits_per_pixel//8)
        # write() reports damage to the DRM driver. mmap alone can leave Intel
        # FBC/PSR scanning a cached login frame although readback has new pixels.
        if rowlen == self.fix.line_length:
            self._write_pixels(data,offset)
        else:
            for row in range(self.height):
                start=offset+row*self.fix.line_length
                self._write_pixels(data[row*rowlen:(row+1)*rowlen],start)

    def _write_pixels(self,data,offset):
        remaining=memoryview(data)
        while remaining:
            count=os.pwrite(self.fd,remaining,offset)
            if count<=0:
                raise OSError('Framebuffer write made no progress')
            offset+=count
            remaining=remaining[count:]

    def close(self):
        if self.graphics:
            try:
                fcntl.ioctl(self.tty_fd,0x4B3A,0)  # Always restore KD_TEXT
            except OSError:
                pass
            finally:
                self.graphics=False
        if self.fd is not None:
            os.close(self.fd)
            self.fd=None
