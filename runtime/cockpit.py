#!/usr/bin/python3
"""Full-screen local rescue cockpit and a concise SSH handover."""
import curses
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time

import network
from i18n import result_text, t

MASCOT = (
    "       .-.       ",
    "      /   \\      ",
    "   (o)| O |(o)   ",
    "      \\~^~/      ",
    "       | |       ",
    "       | |       ",
    "       \\ /       ",
    "        V        ",
)


def version():
    try:
        return Path("/usr/share/aguja/VERSION").read_text().strip()
    except OSError:
        return t("desarrollo")


def ssh_command(address, port):
    option = "" if str(port) == "22" else " -p " + str(port)
    return "ssh" + option + " aguja@" + address


def auth_label(mode):
    return {"locked": t("SSH bloqueado · desbloquea tu perfil en la consola local"), "default": t("Usuario: aguja  |  Contraseña de fábrica: aguja"),
            "custom": t("Usuario: aguja  |  Contraseña personalizada (no se muestra)"),
            "key": t("Usuario: aguja  |  Acceso por tu clave pública SSH")}.get(mode, t("Usuario: aguja  |  Consulta aguja doctor"))


def banner(current=None, compact=False):
    current = current or network.state()
    print("\n"+t("LA AGUJA RESCUE DISK")+" · " + version() + t("   /   Agujita lista para el rescate"))
    if not compact:
        for line in MASCOT:
            print(line)
    print(t("Una entrada pequeña. Control completo.")+"\n")
    addresses = current["addresses"]
    if addresses:
        print("IP: " + "  ".join(a["ip"] for a in addresses))
        print(t("ENTRA POR SSH: ") + ssh_command(addresses[0]["ip"], current["ssh_port"]))
    else:
        print(t("SIN IP DE RED · conectar Wi-Fi: aguja wifi · Ethernet: conecta el cable"))
    ts = current.get("tailscale")
    if ts and ts.get("connected") and ts.get("ipv4"):
        server_label = ts.get("login_server", "Tailscale")
        print(t("RED PRIVADA TAILSCALE: ") + f"{ts['ipv4']} ({server_label})")
        print(t("SSH POR TAILSCALE: ") + ssh_command(ts["ipv4"], current["ssh_port"]))
    if current["mdns"]:
        print(t("NOMBRE EN LA LAN: ") + ssh_command(current["mdns"], current["ssh_port"]))
    print("SSH: " + (t("listo") if current["ssh_active"] else t("iniciando / revisar aguja doctor")))
    print(auth_label(current["ssh_auth_mode"]))
    print(t("\nTerminal: Tab completa · flecha derecha acepta sugerencias · Ctrl-R busca historial"))
    print(t("Ayuda: aguja help  |  Red: aguja wifi  |  Estado: aguja status"))
    print(t("Agente remoto: aguja context  |  Herramientas: aguja tools  |  Root: sudo -n"))
    print(t("Trabajo: ") + current["workspace"] + "\n")


def activity_snapshot():
    try:
        import activity
        return activity.snapshot()
    except (ImportError, OSError, ValueError, RuntimeError):
        return {"sessions": [], "events": [], "processes": []}


def draw(screen, current, countdown=0, selected=0, activity=None,
         paused=False, scroll=0, view="activity", stats=None, tick=0, control=None):
    """Full-width text alternative for serial, SSH and unsupported framebuffers."""
    import display
    screen.erase()
    height, width = screen.getmaxyx()
    activity = activity or {}
    if control:
        activity = control.data(activity)
    stats = stats or {}
    cyan = curses.color_pair(1) | curses.A_BOLD
    gold = curses.color_pair(2) | curses.A_BOLD
    def line(y, text, color=0, x=2, limit=None):
        if 0 <= y < height-1 and 0 <= x < width-1:
            try:
                screen.addnstr(y, x, display.clean(text).replace("\n", " "),
                               max(0,min(width-x-1, limit if limit is not None else width)),color)
            except curses.error:
                pass
    line(0, t("LA AGUJA RESCUE DISK")+"  /  " + version() + t("  /  Consola de rescate"), cyan)
    addresses = current.get("addresses", [])
    ts = current.get("tailscale")
    if ts and ts.get("connected") and ts.get("ipv4"):
        line(2, ssh_command(ts["ipv4"], current.get("ssh_port", 22)) + f"  (Tailscale)", gold)
    elif addresses:
        line(2, ssh_command(addresses[0]["ip"], current.get("ssh_port", 22)), gold)
    else:
        line(2, t('SIN RED · Wi-Fi en {countdown}s', countdown=countdown) if countdown else t("SIN RED · W: Wi-Fi / conecta Ethernet"), gold)
    line(3, "SSH " + (t("listo") if current.get("ssh_active") else t("iniciando")) + "  |  " + (current.get("mdns") or t("mDNS esperando")) +
         f"  |  CPU {stats.get('cpu',0)}%  RAM {stats.get('ram',0)}%",cyan)
    line(4,auth_label(current.get("ssh_auth_mode")),curses.A_DIM)
    line(6, (t("PAUSADA · P continúa") if paused else t("ACTIVIDAD REMOTA EN DIRECTO")) + t('  /  {count} sesión(es)', count=len(display.active_sessions(activity))),cyan)
    side = width >= 110 and view in ("activity", "commands")
    stream_width = width-40 if side else width-4
    capacity = max(0,height-13)
    if view == "commands":
        import panel_state
        commands = activity.get('commands', [])
        chosen = control.selected_command(activity) if control else commands[-1] if commands else None
        if chosen and control and control.detail:
            rows = [chosen.get('title',''), chosen.get('command',''),
                    result_text(chosen.get('result',t('En curso')))+' · '+panel_state.command_duration(chosen,time.time()),
                    'ID: '+chosen.get('id','')+' · '+chosen.get('transport','ssh'),
                    t('Salida privada · disponible por SSH') if chosen.get('output_private') else t('Salida filtrada:')]
            rows += [e.get('text','') for e in activity.get('events',[]) if e.get('kind')=='output' and e.get('command_id')==chosen.get('id')]
            rows=panel_state.wrap_lines(rows,max(1,stream_width-2))
            control.bound_scroll(len(rows),capacity)
            for i,row in enumerate(rows[control.scroll:control.scroll+capacity]):line(8+i,row,limit=stream_width)
        else:
            n=max(1,capacity//3)
            index=commands.index(chosen) if chosen else 0
            start=max(0,min(index-n//2,len(commands)-n))
            for i,c in enumerate(commands[start:start+n]):
                prefix='> ' if c==chosen else '  '
                line(8+3*i,prefix+c.get('title',''),gold if c==chosen else 0,limit=stream_width)
                line(9+3*i,'  '+result_text(c.get('result',t('En curso')))+' · '+panel_state.command_duration(c,time.time()),cyan,limit=stream_width)
                line(10+3*i,'  '+c.get('command','').replace('\n',' ↵ '),curses.A_DIM,limit=stream_width)
        if not commands:line(8,t('Esperando tareas · aguja run --label "Memoria" -- free -h'),cyan,limit=stream_width)
    elif view == "auth":
        import auth
        record=auth.current()
        if record:
            line(7,t('ACCESO: ')+record['provider'],gold)
            try:rows=auth.terminal_lines(record,stream_width,height-8)
            except (ImportError,ValueError):rows=[t('Navegador no disponible; conserva el enlace original.')]
            if rows and rows[0].startswith('\x1b') and curses.has_colors():
                curses.init_pair(3,curses.COLOR_BLACK,curses.COLOR_WHITE)
                for i,row in enumerate(rows):line(8+i,row,curses.color_pair(3))
            else:
                for i,row in enumerate(rows[:capacity]):line(8+i,row)
        else:line(8,t('Sin acceso pendiente. Inicia aguja login claude / antigravity.'),cyan)
        line(height-4,t('A / Esc: volver · navegador en el agente: Ctrl+] · pega el código allí'),gold)
    elif view == "help":
        options = [t("1  Consola Zsh"), t("2  Conectar Wi-Fi"), t("3  Guía y herramientas"), t("8  Diagnóstico"),
                   "4  Codex", "5  Antigravity", "6  Claude Code", "7  OpenCode", t("9  Contraseña SSH"), t("R  Tailscale / Headscale · SSH privado")]
        for i,text in enumerate(options[:capacity]):
            line(8+i,("> " if selected==i else "  ")+text,gold if selected==i else 0)
    elif view == "processes":
        rows = display.process_rows(activity.get("processes",[]))
        for i,(text,state) in enumerate(rows[scroll:scroll+capacity]):
            line(8+i,text+"  ["+state+"]",limit=stream_width)
        if not rows:
            line(8,t("Sin procesos remotos activos."),curses.A_DIM)
    else:
        rows = display.event_rows(activity.get("events",[]))
        wrapped = []
        chars = max(12,stream_width-12)
        for stamp,text,kind in rows:
            wrapped.extend((stamp if i==0 else '',text[i:i+chars],kind) for i in range(0,max(1,len(text)),chars))
        end=max(0,len(wrapped)-scroll)
        for i,(stamp,text,kind) in enumerate(wrapped[max(0,end-capacity):end]):
            line(8+i,stamp+"  "+text,gold if kind=="command" else cyan if kind=="connect" else 0,limit=stream_width)
        if not wrapped:
            line(8,t("Esperando conexión SSH. Los comandos y resultados aparecerán aquí."),curses.A_DIM)
            line(10,t("H: ayuda y herramientas · W: conectar Wi-Fi · Q: consola local"),curses.A_DIM)
        if side:
            x=width-36
            line(7,t("PROCESOS"),cyan,x,34)
            for i,(text,state) in enumerate(display.process_rows(activity.get('processes',[]))[:max(0,capacity-7)]):
                line(9+i,text,0,x,34)
            for i,art in enumerate(MASCOT[-5:]):
                line(height-9+i,art,gold,x+8,24)
    line(height-3,t('↑↓ Elegir / desplazar · Enter / clic Desplegar · Esc Plegar · PgUp/PgDn · S Sesión · F Fallos · B Sondeos · L Directo · Tab Vistas · Q Consola'),curses.A_DIM)
    line(height-2,t("1 Consola  2 Wi-Fi  3 Guía  4 Codex  5 Antigravity  6 Claude  7 OpenCode  8 Estado  9 Clave  R Tailnet"),curses.A_DIM)
    screen.refresh()


def choose(screen, auto_setup=False, delay=12, auth_view=False):
    import display
    from panel_state import PanelState
    control = PanelState()
    if auth_view:control.view="auth"
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
    # Eight animation frames/s. getch blocks between frames rather than spinning.
    screen.timeout(125)
    try:curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
    except curses.error:pass
    start = time.monotonic()
    selection, scroll = 0, 0
    paused = False
    current, snapshot = {}, {}
    next_network = next_activity = next_stats = 0
    resources = display.ResourceStats()
    stats = {}
    fb = None
    pointer = None
    previous_term = signal.getsignal(signal.SIGTERM)
    def stop(signum, frame):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM, stop)
    try:
        try:
            from PIL import Image  # optional: curses works without Pillow
            fb = display.Framebuffer()
            from pointer import Pointer
            pointer = Pointer(fb.width,fb.height)
        except (ImportError, OSError, ValueError, RuntimeError):
            pass
        while True:
            now = time.monotonic()
            if now >= next_network:
                current = network.state()
                next_network = now+3
            if now >= next_activity:
                live = activity_snapshot()
                if not paused:
                    snapshot = live
                else:
                    snapshot = dict(snapshot, sessions=live.get("sessions",[]), processes=live.get("processes",[]))
                next_activity = now+.4
            if now >= next_stats:
                stats = resources.sample()
                next_stats = now+1
            remaining = max(0,delay-int(now-start)) if auto_setup and not current.get("connected") else 0
            if fb:
                try:
                    if pointer:
                        for event in pointer.poll():display.pointer_action(control,snapshot,event,fb.width,fb.height)
                    if control.view=='auth':
                        import auth
                        fb.present(auth.render(fb.width,fb.height,auth.current()))
                    else:
                        fb.present(display.render(fb.width,fb.height,current,snapshot,tick=now-start,
                               paused=paused,scroll=control.scroll,view=control.view,selected=selection,
                               countdown=remaining,stats=stats,release=version(),control=control,pointer=pointer.position if pointer else None))
                except (OSError, ValueError):
                    fb.close()
                    fb = None
                    if pointer:pointer.close();pointer=None
            if fb is None:
                draw(screen,current,remaining,selection,activity=snapshot,paused=paused,
                     scroll=control.scroll,view=control.view,stats=stats,tick=now-start,control=control)
            if auto_setup and not current.get("connected") and not remaining:
                return "wifi"
            key = screen.getch()
            if key == curses.KEY_MOUSE:
                try:
                    _,mx,my,_,buttons=curses.getmouse()
                    if buttons & curses.BUTTON4_PRESSED:control.key('up',snapshot)
                    elif buttons & getattr(curses,'BUTTON5_PRESSED',0):control.key('down',snapshot)
                    elif buttons & curses.BUTTON3_PRESSED:control.key('back',snapshot)
                    elif buttons & (curses.BUTTON1_CLICKED|curses.BUTTON1_PRESSED|curses.BUTTON1_DOUBLE_CLICKED) and control.view=='commands':
                        if control.detail:control.key('back',snapshot)
                        else:
                            import panel_state
                            height,width=screen.getmaxyx()
                            capacity=max(1,max(0,height-13)//3)
                            commands=panel_state.command_window(control.data(snapshot).get('commands',[]),control.selected,capacity)
                            index=(my-8)//3
                            if 8<=my<height-5 and 0<=index<len(commands):control.select(commands[index]['id'],expand=True)
                except curses.error:pass
            elif key in (curses.KEY_UP,curses.KEY_DOWN,curses.KEY_LEFT,curses.KEY_RIGHT):
                if control.view == 'help':
                    movement = {curses.KEY_UP:-1,curses.KEY_DOWN:1,curses.KEY_LEFT:-1,curses.KEY_RIGHT:1}[key]
                    selection = (selection+movement)%10
                else:
                    control.key({curses.KEY_UP:'up',curses.KEY_DOWN:'down',curses.KEY_LEFT:'previous',curses.KEY_RIGHT:'next'}[key],snapshot)
            elif key in (10,13):
                if control.view == "help":
                    return ("shell","wifi","guide","doctor","codex","antigravity","claude","opencode","password","remote")[selection]
                control.key('detail',snapshot)
            elif key in (ord('a'),ord('A')):
                control.view='commands' if control.view=='auth' else 'auth'
            elif key == 27 and control.view=='auth':
                if auth_view:return 'shell'
                control.view='commands'
            elif key == 27 and control.detail:
                control.key('back',snapshot)
            elif key in (ord("q"),ord("Q"),ord("1"),27):
                return "shell"
            elif key in (ord("w"),ord("W"),ord("2")):
                return "wifi"
            elif key in (ord("h"),ord("H")):
                control.view = "help"
            elif key == ord("3"):
                return "guide"
            elif key in (ord("4"),ord("5"),ord("6"),ord("7")):
                return ("codex","antigravity","claude","opencode")[key-ord("4")]
            elif key == ord("8"):
                return "doctor"
            elif key in (ord("r"),ord("R")):
                return "remote"
            elif key == ord("9"):
                return "password"
            elif key in (ord("p"),ord("P")):
                paused = not paused
                next_activity = 0
            elif key == curses.KEY_PPAGE:
                paused = True
                control.key('pageup',snapshot)
            elif key == curses.KEY_NPAGE:
                control.key('pagedown',snapshot)
            elif key == curses.KEY_HOME:
                control.key('home',snapshot)
            elif key == curses.KEY_END and control.detail:
                control.key('end',snapshot)
            elif key == 9:
                if control.view=='auth':control.view='commands'
                else:control.key('tab',snapshot)
            elif key in (ord('s'),ord('S')):
                control.key('sessions',snapshot)
            elif key in (ord('f'),ord('F')):
                control.key('failures',snapshot)
            elif key in (ord('b'),ord('B')):
                control.key('technical',snapshot)
            elif key in (ord('l'),ord('L'),curses.KEY_END):
                control.key('live',snapshot)
                paused = False
                next_activity = 0
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        if pointer is not None:pointer.close()
        if fb is not None:
            fb.close()
        try:
            curses.curs_set(1)
        except curses.error:
            pass


def page(text):
    if sys.stdout.isatty() and shutil.which("less"):
        subprocess.run(["less", "-R", "-F", "-X"], input=text, text=True)
    else:
        print(text)


def guide():
    page(Path("/usr/share/aguja/QUICKSTART.md").read_text())


def menu(auto_setup=False):
    if not sys.stdin.isatty() or os.environ.get("TERM") in (None, "dumb"):
        banner()
        print(t("Consola disponible. Abre el panel con aguja o configura red con aguja wifi."))
        return "shell"
    automatic = auto_setup
    while True:
        try:
            delay = 25 if network.session().get("wifi_configured") else 12
            action = curses.wrapper(choose, automatic, delay)
        except curses.error:
            banner()
            value = input(t("1 Consola / W Wi-Fi / H Ayuda / 4 Codex [1]: ")).strip().lower()
            action = {"w": "wifi", "h": "guide", "4": "codex", "r": "remote"}.get(value, "shell")
        automatic = False
        if action == "shell":
            banner(compact=True)
            return "shell"
        if action in ("codex", "antigravity", "claude", "opencode"):
            return action
        if action == "guide":
            guide()
        elif action == "wifi":
            subprocess.call(["/usr/local/bin/aguja", "wifi"])
        elif action == "doctor":
            subprocess.call(["/usr/local/bin/aguja", "doctor"])
        elif action == "remote":
            subprocess.call(["/usr/local/bin/aguja", "tailscale"])
            print(t("Configura URL del servidor, nombre y clave de alta en Flash Imager → Red privada. SSH conserva la autenticación del perfil."))
        elif action == "password":
            subprocess.call(["/usr/local/bin/aguja", "password"])
        try:
            input(t("\nEnter: volver al panel… "))
        except EOFError:
            return "shell"


def menu_auth():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(t('El navegador se abre desde aguja login; esta vista requiere consola interactiva.'),file=sys.stderr)
        return 1
    curses.wrapper(choose,False,12,True)
    return 0
