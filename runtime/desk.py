#!/usr/bin/python3
"""Local owner desktop: native GTK forms, private stdin IPC, no web admin port."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
from desk_i18n import tr

ASSETS = Path('/usr/share/aguja/desktop')
GUIDES = Path('/usr/share/aguja')
ERROR = 'Operation not completed. Check the fields, connectivity and permissions.'
PAGES = [('home','Home'),('browser','Web browser'),('files','Files'),('cloud','Cloud and NAS'),
         ('tailnet','Private network'),('network','Network'),('updates','Updates'),
         ('guide','Missions and methods'),('backup','Backup planning'),('settings','Settings')]
CLOUD = {
 'drive': [('client_id','Client ID'),('client_secret','Client secret'),('token','Token JSON'),('service_account_file','Service account JSON'),('root_folder_id','Root folder ID')],
 'onedrive': [('client_id','Client ID'),('client_secret','Client secret'),('token','Token JSON'),('drive_id','Drive ID'),('drive_type','Drive type')],
 'dropbox': [('client_id','Client ID'),('client_secret','Client secret'),('token','Token JSON')],
 's3': [('provider','Provider'),('endpoint','Endpoint URL'),('region','Region'),('access_key_id','Access key ID'),('secret_access_key','Secret access key')],
 'sftp': [('host','Host'),('user','User'),('port','Port'),('pass','Password'),('key_file','SSH private key'),('key_file_pass','Key passphrase'),('known_hosts_file','Known hosts file')],
 'smb': [('host','Host'),('user','User'),('pass','Password'),('domain','Domain'),('port','Port')],
 'webdav': [('url','Endpoint URL'),('vendor','Vendor'),('user','User'),('pass','Password'),('bearer_token','Bearer token')],
}
SECRETS = {'client_secret','token','pass','key_file_pass','access_key_id','secret_access_key','bearer_token','auth_key'}


def ipc(action, data=None):
    result = subprocess.run(['sudo','-n','/usr/bin/python3','/usr/lib/aguja/desk_backend.py',action],
                            input=json.dumps(data or {}).encode(), capture_output=True, timeout=65)
    try: value=json.loads(result.stdout)
    except (ValueError,UnicodeError): raise ValueError(ERROR)
    if not value.get('ok'): raise ValueError(ERROR)
    return value


class Desk(Gtk.Window):
    def __init__(self, page='home'):
        super().__init__(title='LA AGUJA · '+tr('Rescue Desk'))
        self.set_wmclass('aguja-desk','AgujaDesk')
        self.set_default_size(1180,760)
        self.connect('delete-event',self.close)
        self.children=[]; self.busy=False; self.inventory=None; self.items=[]; self.choices={}; self.update_signature=None
        self.auth_url=''; self.current=''; self.widgets={}; self.pages={}
        css=Gtk.CssProvider(); css.load_from_path(str(ASSETS/'style.css'))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL); self.add(root)
        bar=Gtk.Box();bar.get_style_context().add_class('spectrum');root.pack_start(bar,False,False,0)
        body=Gtk.Box();root.pack_start(body,True,True,0)
        side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);side.set_size_request(230,-1)
        side.get_style_context().add_class('sidebar');body.pack_start(side,False,False,0)
        side.pack_start(self.label('LA AGUJA', 'title'),False,False,10)
        side.pack_start(self.label('TRANSCENDENCEIA', 'muted'),False,False,0)
        self.nav=Gtk.ListBox();self.nav.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for key,title in PAGES:
            row=Gtk.ListBoxRow();row.page=key;row.add(self.label(tr(title)));self.nav.add(row)
        self.nav.connect('row-selected',lambda _,row:self.show_page(row.page) if row else None)
        side.pack_start(self.nav,True,True,0)
        self.button(side,'Return to cockpit',lambda:self.close())
        self.stack=Gtk.Stack();body.pack_start(self.stack,True,True,0)
        self.status=self.label(tr('Ready'));self.status.set_margin_start(20);self.status.set_margin_end(20)
        self.status.get_style_context().add_class('statusbar');root.pack_end(self.status,False,False,0)
        for key,title in PAGES:
            scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16)
            for name in ('start','end','top','bottom'):getattr(box,'set_margin_'+name)(28)
            box.pack_start(self.label(tr(title),'title'),False,False,0)
            scroll.add(box);self.stack.add_named(scroll,key);self.pages[key]=box
            getattr(self,'page_'+key)(box)
        index=next((i for i,(key,_) in enumerate(PAGES) if key==page),0)
        self.nav.select_row(self.nav.get_row_at_index(index));self.show_all();self.maximize()
        GLib.timeout_add(1500,self.poll_updates)
        if page=='browser':
            try: url=json.loads((Path(os.environ['AGUJA_DESK_REQUEST'])/'request.json').read_text()).get('url')
            except (KeyError,OSError,ValueError):url=None
            if url:self.address.set_text(url);GLib.idle_add(self.browse)

    def label(self,text,style=None):
        label=Gtk.Label(label=text);label.set_xalign(0);label.set_line_wrap(True);label.set_max_width_chars(85)
        if style:label.get_style_context().add_class(style)
        return label

    def note(self,box,text):
        label=self.label(tr(text),'muted');box.pack_start(label,False,False,0);return label

    def button(self,box,text,callback,primary=False):
        button=Gtk.Button(label=tr(text));button.connect('clicked',lambda _:callback())
        if primary:button.get_style_context().add_class('suggested-action')
        box.pack_start(button,False,False,0);return button

    def row(self,box):
        row=Gtk.Box(spacing=10);box.pack_start(row,False,False,0);return row

    def field(self,box,title,secret=False,file=False,directory=False):
        line=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5)
        box.pack_start(line,False,False,0);line.pack_start(self.label(tr(title)),False,False,0)
        row=self.row(line);entry=Gtk.Entry();entry.set_hexpand(True);entry.set_visibility(not secret)
        if secret:entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        row.pack_start(entry,True,True,0)
        if file or directory:self.button(row,'Choose',lambda:self.choose(entry,directory))
        return entry

    def combo(self,box,title,items):
        box.pack_start(self.label(tr(title)),False,False,0)
        combo=Gtk.ComboBoxText()
        for key,label in items:combo.append(key,tr(label))
        combo.set_active(0);box.pack_start(combo,False,False,0);return combo

    def check(self,box,text,value=False):
        button=Gtk.CheckButton(label=tr(text));button.set_active(value);box.pack_start(button,False,False,0);return button

    def choose(self,entry=None,directory=False,callback=None):
        action=Gtk.FileChooserAction.SELECT_FOLDER if directory else Gtk.FileChooserAction.OPEN
        dialog=Gtk.FileChooserDialog(title=tr('Select directory' if directory else 'Select file'),transient_for=self,action=action)
        dialog.add_buttons(tr('Cancel'),Gtk.ResponseType.CANCEL,tr('Choose'),Gtk.ResponseType.OK)
        if dialog.run()==Gtk.ResponseType.OK:
            path=dialog.get_filename()
            if entry is not None:entry.set_text(path)
            if callback:callback(path)
        dialog.destroy()

    def confirm(self,text):
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,text=tr(text))
        result=dialog.run()==Gtk.ResponseType.OK;dialog.destroy();return result

    def perform(self,action,data=None,done=None):
        if self.busy:return
        self.busy=True;self.status.set_text(tr('Working…'))
        def worker():
            try: result=ipc(action,data);error=False
            except (OSError,ValueError,subprocess.SubprocessError):result={};error=True
            def finish():
                self.busy=False;self.status.set_text(tr(ERROR) if error else tr('Ready') if action.endswith(('status','state','scan')) or action=='volumes' else tr('Saved.') if result.get('persistent') else tr('Applied for this RAM session.'))
                if not error and done:done(result)
                return False
            GLib.idle_add(finish)
        threading.Thread(target=worker,daemon=True).start()

    def spawn(self,argv):
        try:
            process=subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                     env=dict(os.environ,BROWSER='/usr/local/bin/aguja-web',AGUJA_COCKPIT='1'))
            self.children.append(process);return process
        except OSError:self.status.set_text(tr(ERROR))

    def show_page(self,key):
        self.current=key;self.stack.set_visible_child_name(key)
        refresh={'cloud':self.refresh_cloud,'tailnet':self.refresh_tailnet,'files':self.refresh_volumes,'network':self.refresh_network}
        if key in refresh:refresh[key]()

    def page_home(self,box):
        mascot=GUIDES/'branding/mascot/idle.png'
        if mascot.exists():
            pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(mascot),160,180,True)
            image=Gtk.Image.new_from_pixbuf(pixbuf);box.pack_start(image,False,False,0)
        self.note(box,'Choose a task. Keep control.')
        self.note(box,'AI agents need Internet and your provider account. No local models are included.')
        self.note(box,'Native disk and file tools remain available offline.')
        for page,text in [('browser','Open browser'),('files','Open files'),('cloud','Cloud and NAS'),('tailnet','Private network')]:
            self.button(box,text,lambda p=page:self.nav.select_row(self.nav.get_row_at_index([x[0] for x in PAGES].index(p))))

    def page_browser(self,box):
        self.note(box,'One browser for everyday work and native agent sign-in.')
        self.engine=self.combo(box,'Browser engine',[('helium','Helium (default)'),('chromium','Chromium (compatibility)')])
        self.address=self.field(box,'Address (optional)')
        self.address.connect('activate',lambda _:self.browse())
        self.button(box,'Open browser',self.browse,True)
        self.note(box,'Cookies are temporary; downloads are saved where you choose.')
        self.note(box,'Helium is beta. Select Chromium if a website needs compatibility.')

    def browse(self,url=None):
        import web
        try:
            runtime=Path('/run/user')/str(os.getuid());runtime.mkdir(mode=0o700,parents=True,exist_ok=True)
            choice=self.engine.get_active_id();(runtime/'aguja-browser').write_text(choice)
            if url is None:url=self.address.get_text().strip() or None
            if url and '://' not in url:
                from urllib.parse import quote
                url='https://'+url if '.' in url and ' ' not in url else 'https://duckduckgo.com/?q='+quote(url)
            self.children.append(web.open_browser(url,directory=runtime/'aguja-web-session',choice=choice))
        except (OSError,ValueError):self.status.set_text(tr(ERROR))
        return False

    def page_files(self,box):
        self.note(box,'Mounted host files are available here. Internal disks are never mounted automatically.')
        self.path=self.field(box,'Files',file=True);self.path.set_text('/data/workspace' if Path('/data/workspace').exists() else str(Path.home()))
        row=self.row(box)
        self.button(row,'Select directory',lambda:self.choose(self.path,True))
        self.button(row,'Open',self.open_path,True)
        row=self.row(box)
        self.button(row,'Yazi explorer',lambda:self.yazi(False))
        self.button(row,'Root file explorer',lambda:self.yazi(True))
        self.volumes_combo=self.combo(box,'Target partition',[])
        self.writable=self.check(box,'Writable mount')
        self.note(box,'Read-only is the default; ext4/XFS journal replay is disabled.')
        row=self.row(box);self.button(row,'Refresh',self.refresh_volumes)
        self.button(row,'Mount selected partition',self.mount_partition)

    def open_path(self):
        import file_open
        try:self.children.append(file_open.open_file(self.path.get_text()))
        except (OSError,ValueError,subprocess.SubprocessError):self.status.set_text(tr(ERROR))

    def yazi(self,root=False):
        import file_open
        path=self.path.get_text() or '/'
        command=['yazi',path]
        if root:command=['sudo','-n','env','DISPLAY='+os.environ.get('DISPLAY',''),'XAUTHORITY='+os.environ.get('XAUTHORITY',''),'YAZI_CONFIG_HOME=/usr/share/aguja/desktop/yazi',*command]
        self.children.append(file_open.terminal(command))

    def refresh_volumes(self):
        def ready(value):
            self.volumes_combo.remove_all()
            def add(dev):
                path=dev.get('path','');mounts=[m for m in dev.get('mountpoints',[]) if m]
                if dev.get('fstype'):
                    size=int(dev.get('size',0))/1024**3
                    self.volumes_combo.append(path,f"{path} · {size:.1f} GiB · {dev.get('fstype')} · {dev.get('label') or ''} · {', '.join(mounts)}")
                for child in dev.get('children',[]):add(child)
            for dev in value.get('devices',[]):add(dev)
            self.volumes_combo.set_active(0)
        self.perform('volumes',done=ready)

    def mount_partition(self):
        device=self.volumes_combo.get_active_id()
        if not device:return
        writable=self.writable.get_active()
        if writable and not self.confirm('Writes affect the selected host partition. Continue only for your intended target.'):return
        self.perform('mount-volume',{'device':device,'writable':writable},lambda result:self.path.set_text(result['mountpoint']))

    def page_cloud(self,box):
        self.cloud_location=self.note(box,'Credentials: RAM only, lost on shutdown. Protect the profile for encrypted persistence.')
        self.remotes=self.combo(box,'Saved destinations',[])
        row=self.row(box);self.button(row,'Refresh',self.refresh_cloud)
        self.button(row,'Check destination',lambda:self.perform('cloud-probe',{'name':self.remotes.get_active_id()},lambda r:self.show_items(r['items'])))
        self.button(row,'Browse destination',self.cloud_browse)
        row=self.row(box)
        self.button(row,'Import config file',lambda:self.choose(callback=lambda p:self.perform('cloud-import',{'path':p},self.cloud_ready)))
        self.button(row,'Import from directory',lambda:self.choose(directory=True,callback=lambda p:self.perform('cloud-import',{'path':p},self.cloud_ready)))
        self.button(box,'Native OAuth / advanced wizard',self.cloud_wizard)
        self.remote_name=self.field(box,'Remote name')
        self.provider=self.combo(box,'Provider',[(x,{'drive':'Google Drive','onedrive':'OneDrive','dropbox':'Dropbox','s3':'S3 compatible','sftp':'SFTP','smb':'SMB / NAS','webdav':'WebDAV'}[x]) for x in CLOUD])
        self.cloud_fields_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.pack_start(self.cloud_fields_box,False,False,0)
        self.cloud_fields={};self.provider.connect('changed',lambda _:self.build_cloud_fields());self.build_cloud_fields()
        self.button(box,'Save remote',self.cloud_save,True)
        self.note(box,'Blank fields preserve stored values. Secrets are not loaded into this form.')
        self.note(box,'No automatic uploads or synchronization.')

    def build_cloud_fields(self):
        for widget in self.cloud_fields_box.get_children():widget.destroy()
        self.cloud_fields={}
        grid=Gtk.Grid(column_spacing=18,row_spacing=14);grid.set_column_homogeneous(True)
        self.cloud_fields_box.pack_start(grid,False,False,0)
        for index,(key,label) in enumerate(CLOUD[self.provider.get_active_id()]):
            cell=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
            grid.attach(cell,index%2,index//2,1,1)
            self.cloud_fields[key]=self.field(cell,label,secret=key in SECRETS,file=key.endswith('_file'))
        self.cloud_fields_box.show_all()

    def cloud_ready(self,result):
        self.remotes.remove_all()
        for remote in result.get('remotes',[]):self.remotes.append(remote['name'],remote['name']+' · '+remote['type'])
        self.remotes.set_active(0)
        self.cloud_location.set_text(tr('Credentials: unlocked LUKS vault.' if result.get('persistent') else 'Credentials: RAM only, lost on shutdown. Protect the profile for encrypted persistence.'))

    def refresh_cloud(self):self.perform('cloud-status',done=self.cloud_ready)

    def cloud_save(self):
        data={'type':self.provider.get_active_id(),'name':self.remote_name.get_text(),'fields':{k:w.get_text() for k,w in self.cloud_fields.items()}}
        def ready(result):
            self.cloud_ready(result)
            for key,entry in self.cloud_fields.items():
                if key in SECRETS:entry.set_text('')
        self.perform('cloud-save',data,ready)

    def show_items(self,items):
        dialog=Gtk.Dialog(title=tr('Check destination'),transient_for=self);dialog.set_default_size(640,420)
        text=Gtk.TextView();text.set_editable(False);text.get_buffer().set_text('\n'.join(items) or tr('Empty destination'))
        scroll=Gtk.ScrolledWindow();scroll.add(text);dialog.get_content_area().pack_start(scroll,True,True,0)
        dialog.add_button(tr('Cancel'),Gtk.ResponseType.CLOSE);dialog.show_all();dialog.run();dialog.destroy()

    def cloud_wizard(self):
        folder=Path(tempfile.mkdtemp(prefix='aguja-rclone-',dir='/tmp'));path=folder/'rclone.conf'
        def seed(_):
            import file_open
            process=file_open.terminal(['rclone','--config',str(path),'config'],'LA AGUJA · OAuth / Cloud')
            self.children.append(process)
            def wait():
                process.wait()
                try:ipc('cloud-wizard',{'path':str(path),'import':True})
                except (OSError,ValueError,subprocess.SubprocessError):pass
                finally:
                    import shutil
                    shutil.rmtree(folder)
                GLib.idle_add(self.refresh_cloud)
            threading.Thread(target=wait,daemon=True).start()
        self.perform('cloud-wizard',{'path':str(path)},seed)

    def cloud_browse(self):
        name=self.remotes.get_active_id()
        if not name:return
        def ready(result):
            import file_open
            self.children.append(file_open.terminal(['yazi',result['mountpoint']]))
        self.perform('cloud-mount',{'name':name},ready)

    def page_tailnet(self,box):
        self.tailnet_state=self.note(box,'Not connected')
        self.tailnet={};self.tailnet['enabled']=self.check(box,'Enable private network',True)
        grid=Gtk.Grid(column_spacing=18,row_spacing=14);grid.set_column_homogeneous(True);box.pack_start(grid,False,False,0)
        for index,(key,label) in enumerate([('login_server','Login server URL'),('hostname','Node hostname'),('auth_key','Auth key (optional)'),('auth_key_file','Auth key file (optional)'),('exit_node','Exit node (IP or name)'),('advertise_routes','Advertised subnets (comma-separated CIDR)'),('advertise_tags','Advertised tags (comma-separated)')]):
            cell=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);grid.attach(cell,index%2,index//2,1,1)
            self.tailnet[key]=self.field(cell,label,secret=key=='auth_key',file=key=='auth_key_file')
        self.note(box,'Empty URL uses Tailscale; Headscale requires your HTTPS URL.')
        self.note(box,'Without a key, use native browser authorization.')
        self.tailnet['netfilter_mode']=self.combo(box,'Netfilter mode',[(x,x) for x in ('on','off','nodivert')])
        grid=Gtk.Grid(column_spacing=18,row_spacing=4);grid.set_column_homogeneous(True);box.pack_start(grid,False,False,0)
        for index,(key,label,default) in enumerate([('accept_routes','Accept routes',False),('accept_dns','Accept DNS',False),('ssh','Tailscale SSH',False),('exit_node_allow_lan_access','Allow LAN access with exit node',False),('advertise_exit_node','Offer this device as exit node',False),('shields_up','Shields up',False),('snat_subnet_routes','SNAT subnet routes',True),('forwarding','Enable IP forwarding on this live',False)]):
            cell=Gtk.Box();grid.attach(cell,index%2,index//2,1,1)
            self.tailnet[key]=self.check(cell,label,default)
        self.note(box,'Routes, tags, exit nodes and SSH also depend on control-plane approvals and policies. Applying network changes may interrupt remote sessions.')
        row=self.row(box);self.button(row,'Connect / apply preferences',self.apply_tailnet,True)
        self.button(row,'Open authorization',lambda:self.browse(self.auth_url) if self.auth_url else None)
        self.button(row,'Refresh',self.refresh_tailnet)

    def refresh_tailnet(self):
        def ready(result):
            data=result['preferences'];self.tailnet_state.set_text(tr('Connected' if result['status'].get('connected') else 'Not connected')+' · '+('LUKS' if data.get('persistent') else 'RAM'))
            for key,widget in self.tailnet.items():
                if key in ('auth_key','auth_key_file'):continue
                if isinstance(widget,Gtk.CheckButton):widget.set_active(bool(data.get(key,False)))
                elif isinstance(widget,Gtk.ComboBoxText):widget.set_active_id(data.get(key) or 'on')
                else:widget.set_text(data.get(key,''))
        self.perform('tailnet-status',done=ready)

    def apply_tailnet(self):
        data={}
        for key,widget in self.tailnet.items():
            data[key]=widget.get_active() if isinstance(widget,Gtk.CheckButton) else widget.get_active_id() if isinstance(widget,Gtk.ComboBoxText) else widget.get_text()
        def ready(result):
            self.auth_url=result.get('auth_url','');self.tailnet_state.set_text(tr('Connected' if result.get('connected') else 'Not connected'))
            self.tailnet['auth_key'].set_text('')
            if self.auth_url:self.browse(self.auth_url)
        self.perform('tailnet-apply',data,ready)

    def page_network(self,box):
        self.network_label=self.note(box,'Ethernet uses automatic configuration unless you change its profile.')
        self.wifi_list=self.combo(box,'SSID',[]);self.wifi_list.connect('changed',lambda w:self.ssid.set_text(w.get_active_id() or '') if hasattr(self,'ssid') else None)
        self.ssid=self.field(box,'SSID');self.wifi_password=self.field(box,'Password',secret=True)
        self.security=self.combo(box,'Security',[('wpa-psk','WPA / WPA2 Personal'),('sae','WPA3 Personal'),('open','Open network')])
        self.hidden=self.check(box,'Hidden network')
        row=self.row(box)
        self.button(row,'Scan Wi-Fi',self.scan_wifi);self.button(row,'Connect',self.connect_wifi,True)
        self.button(box,'Advanced network profiles',lambda:self.spawn(['nm-connection-editor']))
        self.button(box,'Save active Wi-Fi for next boot',lambda:self.perform('wifi-save'))

    def refresh_network(self):
        def ready(result):
            addresses=', '.join(a['ip'] for a in result.get('addresses',[]))
            self.network_label.set_text((tr('Connected') if result.get('connected') else tr('Not connected'))+' · '+addresses)
        self.perform('network-status',done=ready)

    def scan_wifi(self):
        def ready(result):
            self.wifi_list.remove_all()
            for fields in result['networks']:
                if fields and fields[0]:self.wifi_list.append(fields[0],' · '.join(fields))
            self.wifi_list.set_active(0)
        self.perform('wifi-scan',done=ready)

    def connect_wifi(self):
        data={'ssid':self.ssid.get_text(),'password':self.wifi_password.get_text(),'security':self.security.get_active_id(),'hidden':self.hidden.get_active()}
        self.perform('wifi-connect',data,lambda _:self.wifi_password.set_text(''))

    def page_updates(self,box):
        self.note(box,'Full Rescue needs persistent storage; All RAM selects components only.')
        row=self.row(box);self.button(row,'Check updates',lambda:self.perform('update-submit',{'operation':'check'},self.accept_updates),True)
        row=self.row(box)
        for label,mode in [('All · No','no'),('All · RAM','session'),('All · persistent','persistent')]:self.button(row,label,lambda m=mode:self.all_updates(m))
        self.update_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);box.pack_start(self.update_box,False,False,0)
        self.update_message=self.note(box,'Installed → available')
        self.button(box,'Review selection',self.review_updates,True)

    def all_updates(self,mode):
        skipped=0
        for item in self.items:
            value='no' if item['kind']=='release' and mode=='session' else mode
            skipped+=value!=mode;self.choices[item['id']]=value
            self.widgets[item['id']].set_active_id(value)
        if skipped:self.update_message.set_text(tr('Full Rescue needs persistent storage; All RAM selects components only.'))

    def accept_updates(self,result):
        job=result.get('job')
        inventory=result.get('inventory')
        if job:
            if job.get('operation')=='check' and job.get('state')=='done':inventory=job.get('result')
            event=job.get('event') or {};message=event.get('detail') or job.get('state','')
            self.update_message.set_text(str(message))
            if job.get('state') in ('failed','done') and job.get('operation')=='apply':
                value=job.get('result',{})
                self.update_message.set_text(tr('Restart required; previous and factory generations remain available.') if value.get('reboot_required') else str(value.get('error') or message))
        if not inventory:return
        signature=json.dumps(inventory,sort_keys=True)
        if signature==self.update_signature:return
        self.update_signature=signature;self.inventory=inventory
        import update_tasks
        self.items=update_tasks.rows(inventory);self.choices={i['id']:'no' for i in self.items};self.widgets={}
        for child in self.update_box.get_children():child.destroy()
        for item in self.items:
            row=self.row(self.update_box);label=self.label(item['name']+'\n'+str(item['current'])+' → '+str(item['latest']))
            label.set_hexpand(True);row.pack_start(label,True,True,0)
            combo=Gtk.ComboBoxText()
            for mode,title in [('no','No'),('session','Yes · RAM'),('persistent','Yes · persistent')]:
                if item['kind']!='release' or mode!='session':combo.append(mode,tr(title))
            combo.set_active_id('no');combo.connect('changed',lambda w,k=item['id']:self.choices.update({k:w.get_active_id()}))
            row.pack_end(combo,False,False,0);self.widgets[item['id']]=combo
        self.update_box.show_all()

    def poll_updates(self):
        if self.current=='updates' and not self.busy:self.perform('update-state',done=self.accept_updates)
        return True

    def review_updates(self):
        selected=[i['name']+' · '+tr('Yes · RAM' if self.choices[i['id']]=='session' else 'Yes · persistent') for i in self.items if self.choices.get(i['id'],'no')!='no']
        if selected and self.confirm(tr('Apply selection')+'?\n\n'+'\n'.join(selected)):
            self.perform('update-submit',{'operation':'apply','items':self.items,'choices':self.choices},self.accept_updates)

    def page_guide(self,box):
        self.note(box,'Canonical agent instructions are in English. Agents should answer in your chosen language.')
        self.note(box,'Observe → choose backup → act → verify → hand over')
        for title,name in [('Read the agent guide','AGENT-CONTEXT.md'),('Read ODD workflow','ODD.md'),('Mission','MISSIONS.md'),('Read backup methods','BACKUP.md')]:
            self.button(box,title,lambda n=name:self.spawn(['mousepad',str(GUIDES/n)]))

    def page_backup(self,box):
        self.note(box,'Choose only a feasible destination and measure its free space. Same-disk copies do not protect against disk failure.')
        self.goal=self.field(box,'Goal / exact target')
        self.backup_choice=self.combo(box,'Decision',[(str(i),s) for i,s in enumerate(['Separate disk','External disk','NAS / SSH','Cloud (ask first)','Rescue USB DATA (temporary)','Same-disk partition (limited)','No backup (explicit decision)'])])
        self.note(box,'A note is a plan, not authorization for new destructive actions.')
        self.button(box,'Read backup methods',lambda:self.spawn(['mousepad',str(GUIDES/'BACKUP.md')]))
        self.button(box,'Create mission note',self.mission_note,True)

    def mission_note(self):
        folder=Path('/data/workspace' if Path('/data/workspace').exists() else str(Path.home()/'workspace'))/'odd/tasks'
        folder.mkdir(parents=True,exist_ok=True)
        from datetime import datetime
        path=folder/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-mission.md')
        path.write_text('# Mission\n\nOwner: live operator\nGoal / exact target: '+self.goal.get_text()+'\nBackup preference to assess: '+self.backup_choice.get_active_text()+'\n\nScope / exclusions:\n- To agree with the operator. This note does not authorize destructive actions.\n\nObserved baseline:\n- Pending live inspection.\n\nTasks:\n- [ ] Observe sources, destinations and resources\n- [ ] Agree protection/rollback and scope\n- [ ] Perform authorized work\n- [ ] Verify observable outcome\n\nEvidence:\n- Pending\n\nNext action:\n- Read /usr/share/aguja/ODD.md and inspect the actual target.\n')
        self.spawn(['mousepad',str(path)])

    def page_settings(self,box):
        self.note(box,'Canonical agent instructions are in English. Agents should answer in your chosen language.')
        self.note(box,'No provider credentials are included in the image.')
        self.new_password=self.field(box,'New SSH password',secret=True);self.repeat_password=self.field(box,'Repeat password',secret=True)
        def save():
            def ready(_):self.new_password.set_text('');self.repeat_password.set_text('')
            self.perform('ssh-password',{'password':self.new_password.get_text(),'confirmation':self.repeat_password.get_text()},ready)
        self.button(box,'Save SSH password',save,True)
        self.button(box,'Language and keyboard',lambda:self.terminal(['/usr/local/bin/aguja','locale']))

    def terminal(self,argv):
        import file_open
        self.children.append(file_open.terminal(argv))

    def close(self,*_):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:child.kill()
        Gtk.main_quit();return False


if __name__=='__main__':
    if os.getuid()==0:raise SystemExit('Desktop applications run as the owner, never root.')
    Desk(sys.argv[1] if len(sys.argv)>1 else 'home');Gtk.main()
