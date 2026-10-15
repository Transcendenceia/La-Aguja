"""Interactive update browser for the real local framebuffer and terminal/SSH."""
import curses,queue,sys,threading,time,math
from collections import deque
import update_tasks as tasks
import update_progress as progress
import updates
from i18n import t

class Model:
 def __init__(self):
  self.target=None;self.mode=None;self.phase='home';self.inventory=None;self.items=[];self.choices={};self.selected=0;self.offset=0;self.event={};self.events=deque(maxlen=8);self.result=None;self.error='';self.focus=0;self.pending=queue.Queue();self.thread=None
 @property
 def busy(self):return self.phase in ('checking','applying')
 def start(self,operation):
  if self.busy:return
  if operation=='apply':
   chosen=tasks.plan(self.items,self.choices)
   if not any(chosen.values()):self.error='Selecciona al menos una actualización.';return
  self.phase='checking' if operation=='check' else 'applying';self.error='';self.event={};self.events.clear();self.result=None
  items=[dict(r) for r in self.items];choices=dict(self.choices)
  def worker():
   try:
    with progress.listen(lambda e:self.pending.put(('event',e))):result=updates.check() if operation=='check' else tasks.apply(items,choices)
    self.pending.put((operation,result))
   except Exception as e:
    self.pending.put(('error',str(e) if isinstance(e,ValueError) else 'No se completó esta operación. Revisa el estado antes de reintentar.'))
  self.thread=threading.Thread(target=worker,name='aguja-update',daemon=False);self.thread.start()
 def drain(self):
  while True:
   try:kind,value=self.pending.get_nowait()
   except queue.Empty:return
   if kind=='event':
    self.event=value
    if value.get('mode'):self.mode=value['mode']
    if not self.events or (value.get('stage'),value.get('detail'))!=(self.events[-1].get('stage'),self.events[-1].get('detail')):self.events.append(value)
   elif kind=='check':
    self.inventory=value;self.items=tasks.rows(value);self.choices={r['id']:'no' for r in self.items};self.selected=0;self.offset=0;self.focus=0;self.phase='list'
   elif kind=='apply':self.result=value;self.phase='done';self.focus=0
   else:self.error=value;self.result={'ok':False,'error':value};self.phase='done'
 def select(self,index,mode):
  if self.phase!='list' or not 0<=index<len(self.items):return
  row=self.items[index]
  if row['kind']=='release' and mode=='session':self.error='El Rescue Disk completo requiere Sí persistente y el próximo arranque.';return
  self.selected=index;self.choices[row['id']]=mode;self.error=''
 def cycle(self,direction=1):
  if not self.items:return
  row=self.items[self.selected];modes=('no','persistent') if row['kind']=='release' else tasks.MODES
  self.select(self.selected,modes[(modes.index(self.choices[row['id']])+direction)%len(modes)])
 def back(self):
  if self.busy:return False
  if self.phase=='home':return True
  self.phase='home';self.error='';return False

STAGES={'check':'Comprobando actualizaciones','prepare':'Preparando un sistema limpio','download':'Descargando','install':'Instalando','save':'Guardando en el pendrive','verify':'Verificando','activate':'Preparando el próximo arranque','start':'Iniciando','group_done':'Completado'}
LABELS={'no':'No','session':'Sí · RAM','persistent':'Sí persistente'}
MESSAGES=set(STAGES.values())|{'Paquetes del sistema','Rescue Disk','Preparando un sistema limpio','Descargando Rescue Disk','Instalando las actualizaciones seleccionadas','Guardando el sistema en el pendrive','Verificando los archivos guardados','Preparando el próximo arranque','Sí persistente','Sí · solo esta sesión','Guardado y verificado','Actualizado en RAM','Actualizando los paquetes en RAM','Verificando las versiones de esta sesión'}

def measurement(event):
 done,total=event.get('completed'),event.get('total')
 if not isinstance(done,(int,float)) or not math.isfinite(done) or done<0:return ''
 if event.get('unit')=='bytes':
  return f'{done/1024**2:.1f} MiB'+(f' / {total/1024**2:.1f} MiB' if isinstance(total,(int,float)) and total>0 else '')
 if event.get('unit')=='apt' and total==100 and done<=100:return f'APT {done:.0f}%'
 return ''

def menu(language=None):
 if not sys.stdin.isatty() or not sys.stdout.isatty():
  print(t('Usa aguja update check --json para una consulta no interactiva.',language=language));return 1
 tr=lambda text:t(text,language=language)
 model=Model()
 def interact(screen):
  import display
  fb=pointer=None;boxes=[]
  try:
   try:
    fb=display.Framebuffer()
    if fb.width<800 or fb.height<500:fb.close();fb=None
    from pointer import Pointer
    pointer=Pointer(fb.width,fb.height) if fb else None
   except (OSError,ValueError,RuntimeError,ImportError):pass
   try:curses.curs_set(0)
   except curses.error:pass
   screen.timeout(120);screen.keypad(True)
   def text_for_event(e):
    detail=e.get('detail','');return tr(detail) if detail in MESSAGES else display.clean(detail)
   def draw():
    nonlocal boxes
    boxes=[];screen.erase();h,w=screen.getmaxyx()
    if fb:
     from PIL import Image,ImageDraw
     image=Image.new('RGB',(fb.width,fb.height),display.BG);canvas=ImageDraw.Draw(image)
     scale=max(.7,min(fb.width/1280,fb.height/720,1.6));margin=round(28*scale);line=round(35*scale);body_top=round(108*scale);bottom=fb.height-round(112*scale)
     font=display.font(round(18*scale),language=language);small=display.font(round(15*scale),language=language);bold=display.font(round(20*scale),bold=True,language=language);title=display.font(round(28*scale),bold=True,language=language)
     def write(y,text,color=display.WHITE,x=None,large=False):
      x=margin if x is None else x
      canvas.text((x,y),display.clean(text).replace('\n',' '),font=title if large else font,fill=color)
     def button(text,action,x,y,width=None,enabled=True):
      width=width or round(260*scale);box=(x,y,x+width,y+round(44*scale));canvas.rounded_rectangle(box,radius=8,fill=display.CARD,outline=display.CYAN if enabled else display.EDGE,width=2);canvas.text((x+12,y+round(9*scale)),text,font=small,fill=display.WHITE if enabled else display.DIM)
      if enabled:boxes.append((box,action))
     write(margin,tr('LA AGUJA · Actualizaciones'),display.CYAN,large=True)
     write(margin+round(43*scale),tr('Comprueba primero. Tú decides qué actualizar y dónde guardarlo.'),display.DIM)
     y=body_top
     if model.phase=='home':
      write(y,tr('1. Comprobar actualizaciones'),display.WHITE);y+=line*2
      write(y,tr('No: no cambia nada.'));y+=line
      write(y,tr('Sí: actualiza solo esta sesión en RAM.'));y+=line
      write(y,tr('Sí persistente: guarda en el pendrive para el próximo arranque.'));y+=line*2
      button(tr('C · Comprobar actualizaciones'),'check',margin,y,round(360*scale))
      button(tr('Esc · Volver al menú'),'exit',margin,fb.height-round(72*scale))
     elif model.phase=='list':
      count=len(model.items);write(y,tr('Actualizaciones disponibles: {count}').format(count=count),display.GOLD);y+=line
      if model.inventory.get('restart_required'):write(y,tr('Hay una generación guardada pendiente de reinicio.'),display.GOLD);y+=line
      if model.inventory.get('errors'):write(y,tr('Consulta incompleta: algunas fuentes no respondieron.'),display.RED);y+=line
      capacity=max(1,int((bottom-y-line)/line));model.offset=max(0,min(model.offset,max(0,count-capacity)))
      if model.selected<model.offset:model.offset=model.selected
      if model.selected>=model.offset+capacity:model.offset=model.selected-capacity+1
      name_x=margin;version_x=round(fb.width*.35);modes_x=[round(fb.width*x) for x in (.64,.72,.82)];mode_widths=[round(fb.width*x) for x in (.065,.09,.16)]
      for x,text in zip(modes_x,[tr('No'),tr('Sí · RAM'),tr('Sí persistente')]):canvas.text((x,y),text,font=small,fill=display.CYAN)
      y+=line
      if not count:write(y,tr('No hay actualizaciones confirmadas; consulta incompleta.' if model.inventory.get('errors') else 'No hay actualizaciones disponibles.'),display.GREEN)
      for index,row in enumerate(model.items[model.offset:model.offset+capacity],model.offset):
       if index==model.selected:canvas.rounded_rectangle((margin-8,y-3,fb.width-margin,y+line-3),radius=6,fill=display.CARD)
       name=display.clean(row['name']);limit=max(10,int(fb.width*.31/(font.getlength('M') or 10)));name=name if len(name)<=limit else name[:limit-1]+'…'
       canvas.text((name_x,y),name,font=font,fill=display.WHITE);canvas.text((version_x,y),display.clean(str(row['current']))+' → '+display.clean(row['latest']),font=small,fill=display.DIM)
       for mode,x,width in zip(tasks.MODES,modes_x,mode_widths):
        allowed=not(row['kind']=='release' and mode=='session');selected=model.choices[row['id']]==mode
        text=('●' if selected else '○') if allowed else '—'
        canvas.text((x+width//3,y),text,font=font,fill=display.GREEN if selected else display.DIM)
        if allowed:boxes.append(((x,y,x+width,y+line),('select',index,mode)))
       y+=line
      if not model.error:write(bottom+round(5*scale),tr('Flechas: elegir · Espacio: cambiar · A: aplicar · C: consultar'),display.DIM)
      button(tr('A · Revisar selección'),'review',margin,fb.height-round(65*scale),round(300*scale),enabled=any(v!='no' for v in model.choices.values()))
      button(tr('C · Comprobar'),'check',margin+round(320*scale),fb.height-round(65*scale),round(230*scale))
      button(tr('Esc · Volver'),'home',fb.width-margin-round(200*scale),fb.height-round(65*scale),round(200*scale))
     elif model.phase=='confirm':
      chosen=tasks.plan(model.items,model.choices);write(y,tr('Revisa antes de aplicar'),display.GOLD);y+=line*1.5
      for mode in ('session','persistent'):
       group=chosen[mode]
       write(y,tr(LABELS[mode])+': '+str(len(group)),display.CYAN);y+=line
       names=', '.join(r['name'] for r in group) or '—'
       # Long selections are summarized here; the full per-item list remains on Back.
       write(y,display.clean(names)[:max(40,int(fb.width/(font.getlength('M') or 12)))-5]);y+=line*1.5
      if model.target:write(y,tr('Destino persistente: {device}').format(device=model.target['disk']+' · DATA '+model.target['data']),display.CYAN);y+=line
      write(y,tr('Se instalarán también las dependencias necesarias.'));y+=line
      write(y,tr('RAM se pierde al reiniciar. Persistente se aplica en el próximo arranque.'));y+=line
      write(y,tr('No se reinicia el equipo automáticamente.'));y+=line*1.5
      button(tr('Enter · Aplicar selección'),'apply',margin,y,round(340*scale));button(tr('Esc · Revisar lista'),'list',margin+round(360*scale),y,round(290*scale))
     elif model.busy:
      mark='◐◓◑◒'[int(time.monotonic()*5)%4];write(y,mark+'  '+tr(STAGES.get(model.event.get('stage'),'Comprobando actualizaciones' if model.phase=='checking' else 'Iniciando')),display.GOLD);y+=line*1.5
      if model.phase=='applying' and model.mode:write(y,tr(LABELS[model.mode]),display.CYAN);y+=line
      write(y,text_for_event(model.event));y+=line
      measured=measurement(model.event)
      if measured:write(y,measured,display.CYAN);y+=line
      total=model.event.get('total');done=model.event.get('completed')
      if isinstance(total,(float,int)) and total>0 and isinstance(done,(float,int)) and 0<=done<=total:
       bar=(margin,y,fb.width-margin,y+round(13*scale));canvas.rectangle(bar,fill=display.EDGE);canvas.rectangle((margin,y,margin+(fb.width-2*margin)*done/total,bar[3]),fill=display.CYAN);y+=line
      for event in list(model.events)[-6:]:
       if y>=bottom:break
       write(y,tr(STAGES.get(event.get('stage'),'Iniciando'))+' · '+text_for_event(event),display.DIM);y+=line
      write(fb.height-round(65*scale),tr('Espera a que termine; no retires el pendrive.'),display.GOLD)
     elif model.phase=='done':
      result=model.result or {};ok=result.get('ok',False);write(y,tr('Actualización terminada' if ok else 'La actualización no terminó'),display.GREEN if ok else display.RED);y+=line*1.5
      if result.get('error'):write(y,tr(result['error']),display.RED);y+=line*2
      for item in result.get('results',[]):
       write(y,tr('Guardado en el pendrive y verificado' if item['mode']=='persistent' else 'Actualizado en RAM · solo esta sesión'),display.CYAN);y+=line
      if result.get('reboot_required'):write(y,tr('Reinicio pendiente: fábrica y versión anterior siguen disponibles.'));y+=line
      if result.get('session_may_be_partial'):write(y,tr('Puede haber cambios parciales en RAM; revisa antes de reintentar.'),display.GOLD);y+=line
      button(tr('Enter · Volver al menú'),'exit',margin,max(y+line,fb.height-round(85*scale)),round(350*scale))
     if model.error and model.phase!='done':write(fb.height-round(103*scale),tr(model.error),display.RED)
     if pointer and pointer.position:
      x,y=pointer.position;canvas.ellipse((x-4,y-4,x+4,y+4),fill=display.WHITE)
     fb.present(image);return
    # Exact same controller and plan on serial/SSH: no fake progress or auto-approval.
    def line(y,text):
     if 0<=y<h-1:
      try:screen.addnstr(y,1,display.clean(text).replace('\n',' '),max(1,w-2))
      except curses.error:pass
    line(0,tr('LA AGUJA · Actualizaciones'))
    if model.phase=='home':
     for n,text in enumerate(['C · Comprobar actualizaciones','No: no cambia nada.','Sí: actualiza solo esta sesión en RAM.','Sí persistente: guarda en el pendrive para el próximo arranque.','Esc · Volver al menú'],3):line(n,tr(text))
    elif model.phase=='list':
     line(2,tr('Actualizaciones disponibles: {count}').format(count=len(model.items)))
     size=max(1,h-9);model.offset=max(0,min(model.selected-size+1,model.offset));
     if model.selected>=model.offset+size:model.offset=model.selected-size+1
     for n,row in enumerate(model.items[model.offset:model.offset+size]):
      index=n+model.offset;mode='['+tr(LABELS[model.choices[row['id']]])+']';name_width=max(8,min(30,(w-len(mode)-6)//2));version_width=max(4,w-len(mode)-name_width-6);versions=str(row['current'])+' → '+row['latest'];line(4+n,('> ' if index==model.selected else '  ')+row['name'][:name_width].ljust(name_width)+' '+versions[:version_width].ljust(version_width)+' '+mode)
     if model.inventory.get('errors'):line(h-5,tr('Consulta incompleta: algunas fuentes no respondieron.'))
     if not model.items:line(4,tr('No hay actualizaciones disponibles.'))
     line(h-3,tr('Flechas: elegir · Espacio: cambiar · A: aplicar · C: consultar'))
    elif model.phase=='confirm':
     line(2,tr('Revisa antes de aplicar'));chosen=tasks.plan(model.items,model.choices)
     for n,mode in enumerate(('session','persistent')):line(4+n,tr(LABELS[mode])+': '+', '.join(r['name'] for r in chosen[mode]))
     line(7,tr('Se instalarán también las dependencias necesarias.'));line(8,tr('RAM se pierde al reiniciar. Persistente se aplica en el próximo arranque.'));line(10,tr('Enter · Aplicar selección'));line(11,tr('Esc · Revisar lista'))
    elif model.busy:
     line(3,'|/-\\'[int(time.monotonic()*5)%4]+' '+tr(STAGES.get(model.event.get('stage'),'Iniciando')));line(5,text_for_event(model.event));line(6,measurement(model.event))
     for n,event in enumerate(list(model.events)[-max(1,h-12):],8):line(n,tr(STAGES.get(event.get('stage'),'Iniciando'))+' · '+text_for_event(event))
     line(h-3,tr('Espera a que termine; no retires el pendrive.'))
    else:
     result=model.result or {};line(3,tr('Actualización terminada' if result.get('ok') else 'La actualización no terminó'))
     line(5,tr(result.get('error','Reinicio pendiente: fábrica y versión anterior siguen disponibles.' if result.get('reboot_required') else 'Actualizado en RAM · solo esta sesión')));line(h-3,tr('Enter · Volver al menú'))
    if model.error:line(h-2,tr(model.error))
    screen.refresh()
   def action(value):
    if model.busy:return False
    if isinstance(value,tuple):model.select(value[1],value[2]);return False
    if value=='check':model.start('check')
    elif value=='review':
     try:
      chosen=tasks.plan(model.items,model.choices)
      if any(chosen.values()):
       model.target=updates.verify_persistent_target() if chosen['persistent'] else None
       model.phase='confirm';model.error=''
      else:model.error='Selecciona al menos una actualización.'
     except ValueError as e:model.error=str(e)
    elif value=='apply':model.start('apply')
    elif value=='home':model.back()
    elif value=='list':model.phase='list';model.error=''
    elif value=='exit':return True
    return False
   rendered=None
   while True:
    model.drain()
    signature=(model.phase,model.selected,model.offset,repr(model.choices),repr(model.event),repr(model.result),model.error,pointer.position if pointer else None)
    if model.busy or signature!=rendered:draw();rendered=signature
    if pointer:
     for e in pointer.poll():
      if e['action']=='back' and not model.busy:
       if model.back():return 0
      elif e['action'] in ('wheel-up','wheel-down') and model.phase=='list' and model.items:
       model.selected=max(0,min(len(model.items)-1,model.selected+(-1 if e['action']=='wheel-up' else 1)))
      elif e['action']=='click':
       for (x,y,r,b),target in boxes:
        if x<=e['x']<=r and y<=e['y']<=b:
         if action(target):return 0
         break
    try:key=screen.getch()
    except KeyboardInterrupt:
     if model.busy:continue
     return 0
    if model.busy:continue
    if key==27:
     if model.phase=='done':return 0
     if model.phase=='confirm':model.phase='list'
     elif model.back():return 0
    elif key in (ord('c'),ord('C')) and model.phase in ('home','list'):action('check')
    elif key in (10,13):
     if model.phase=='home':action('check')
     elif model.phase=='list':action('review')
     elif model.phase=='confirm':action('apply')
     elif model.phase=='done':return 0
    elif model.phase=='list':
     if key==curses.KEY_UP:model.selected=max(0,model.selected-1)
     elif key==curses.KEY_DOWN:model.selected=min(max(0,len(model.items)-1),model.selected+1)
     elif key==curses.KEY_NPAGE:model.selected=min(max(0,len(model.items)-1),model.selected+8)
     elif key==curses.KEY_PPAGE:model.selected=max(0,model.selected-8)
     elif key in (curses.KEY_RIGHT,32):model.cycle(1)
     elif key==curses.KEY_LEFT:model.cycle(-1)
     elif key in (ord('a'),ord('A')):action('review')
  finally:
   if pointer:pointer.close()
   if fb:fb.close()
 try:return curses.wrapper(interact)
 except curses.error:
  print(tr('No se pudo abrir la interfaz; usa aguja update check --json.'));return 1
