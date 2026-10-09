import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
import activity
import panel_state
import display
import pointer
loader=importlib.machinery.SourceFileLoader('aguja_cli',str(ROOT/'runtime/aguja'))
spec=importlib.util.spec_from_loader(loader.name,loader)
cli=importlib.util.module_from_spec(spec);loader.exec_module(cli)


class ProbeTests(unittest.TestCase):
    def test_only_generated_readonly_probes_outside_git_are_classified(self):
        with tempfile.TemporaryDirectory() as directory:
            command=f'PATH=/usr/bin:/usr/games;cd {directory};git diff --stat'
            self.assertEqual(activity.probe_context(command)['verb'],'diff')
            self.assertEqual(activity.probe_context(f'PATH=/usr/bin;cd {directory};git rev-parse --git-dir')['verb'],'rev-parse')
            fallback=f'PATH=/usr/bin;cd {directory} && GIT_OPTIONAL_LOCKS=0 git symbolic-ref --short HEAD 2> /dev/null || GIT_OPTIONAL_LOCKS=0 git rev-parse --short HEAD 2> /dev/null'
            self.assertEqual(activity.probe_context(fallback)['kind'],'git_workspace')
            self.assertEqual(activity.probe_context(f'PATH=/usr/bin;cd {directory};GIT_OPTIONAL_LOCKS=0 git -c core.quotepath=false log -1')['verb'],'log')
            for command in [f'cd {directory};git diff --stat',f'PATH=/usr/bin;cd {directory};git push',
                            f'PATH=/usr/bin;cd {directory};git diff --no-index a b',
                            f'PATH=/usr/bin;cd {directory};git status;echo secret']:
                self.assertIsNone(activity.probe_context(command))
            (Path(directory)/'.git').mkdir()
            self.assertIsNone(activity.probe_context(f'PATH=/usr/bin;cd {directory};git status'))

    def test_probe_failure_and_signal_never_change_real_exit_code(self):
        self.assertEqual(activity.result_state(128,{'kind':'git_workspace'})[0],'probe')
        self.assertEqual(activity.result_state(129)[0],'error')
        self.assertEqual(activity.result_state(-1)[0],'cancelled')
        self.assertIn('SIGHUP',activity.result_state(-1)[1])


class CommandLifecycleTests(unittest.TestCase):
    def test_labelled_tasks_coalesce_outer_wrapper_and_retain_output_link(self):
        sid='a'*24;uid=os.getuid()
        procs={10:{'pid':10,'ppid':1,'start_ticks':1,'command':'python3 ssh_session.py'},
               11:{'pid':11,'ppid':10,'start_ticks':2,'command':'aguja run'}}
        m=activity.Monitor()
        def emit(kind,pid=10,**fields):m.event(dict(kind=kind,session=sid,**fields),pid,uid,procs)
        emit('session_start',text='aguja [argumentos ocultos]',mode='exec',sensitive=True,label='Memoria')
        emit('command_start',11,text='free -h',label='Memoria',sensitive=False)
        self.assertEqual(len(m.commands),1)
        command=next(iter(m.commands.values()))
        self.assertFalse(command['output_private'])
        emit('output',chunk='TGludXgK')
        self.assertEqual(m.events[-1]['command_id'],command['id'])
        emit('command_end',11,text='1')
        emit('session_end',exit=1)
        self.assertEqual(command['exit'],1)
        self.assertEqual(command['status'],'error')

    def test_command_retention_is_bounded_without_hiding_live_sessions(self):
        sid='a'*24;m=activity.Monitor();m.sessions[sid]={'command':'x'}
        for i in range(activity.MAX_COMMANDS+10):m.begin_command(sid,'test')
        self.assertEqual(len(m.commands),activity.MAX_COMMANDS)
        self.assertEqual(list(m.commands.values())[-1]['status'],'running')

    def test_monitor_restart_preserves_trace_and_never_claims_running_job_succeeded(self):
        m=activity.Monitor({'known-secret'})
        m.restore_history({'commands':[{'id':'s:42','title':'Task','command':'echo known-secret','status':'running'}]})
        row=m.commands['s:42']
        self.assertEqual(row['status'],'disconnected')
        self.assertIsNone(row['exit']);self.assertEqual(m.command_number,42)
        self.assertNotIn('known-secret',row['command'])


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.data={'commands':[{'id':'1','session':'a','status':'ok'},
                               {'id':'2','session':'b','status':'error'},
                               {'id':'3','session':'c','status':'probe','technical':True}],
                   'events':[],'processes':[],'sessions':[]}
        self.p=panel_state.PanelState()
        self.p.view="commands"

    def test_selection_detail_filters_and_live_are_local_only(self):
        self.assertEqual(self.p.selected_command(self.p.data(self.data))['id'],'2')
        self.p.key('up',self.data);self.p.key('detail',self.data)
        self.assertTrue(self.p.detail);self.assertEqual(self.p.selected,'1')
        self.p.key('failures',self.data)
        self.assertEqual(len(self.p.data(self.data)['commands']),1)
        self.p.key('live',self.data);self.assertFalse(self.p.detail)
        self.p.key('failures',self.data);self.p.key('technical',self.data)
        self.assertEqual(len(self.p.data(self.data)['commands']),3)
        self.p.key('sessions',self.data)
        self.assertEqual(self.p.session,'a')
        self.assertEqual(len(self.data['commands']),3)

    def test_all_views_cycle_and_selection_survives_expired_item(self):
        for _ in range(4):self.p.key('tab',self.data)
        self.assertEqual(self.p.view,'commands')
        self.p.selected='expired'
        self.assertEqual(self.p.selected_command(self.p.data(self.data))['id'],'2')

    def test_expanded_command_is_pinned_and_scroll_does_not_change_selection(self):
        self.p.key('detail',self.data)
        self.assertEqual(self.p.selected,'2')
        self.data['commands'].append({'id':'4','session':'b','status':'running'})
        self.assertEqual(self.p.selected_command(self.p.data(self.data))['id'],'2')
        self.p.bound_scroll(100,10)
        self.p.key('down',self.data);self.assertEqual(self.p.scroll,1)
        self.p.key('pagedown',self.data);self.assertEqual(self.p.scroll,11)
        self.p.key('end',self.data);self.assertEqual(self.p.scroll,90)
        self.p.key('pageup',self.data);self.assertEqual(self.p.scroll,80)
        self.p.key('home',self.data);self.assertEqual(self.p.scroll,0)
        self.p.key('next',self.data);self.assertEqual(self.p.selected,'4')
        self.assertTrue(self.p.detail)

    def test_mouse_hit_test_opens_card_and_ignores_sidebar(self):
        x,y,right,bottom,card=display.command_geometry(1280,720)
        display.pointer_action(self.p,self.data,{'action':'click','x':int(x+10),'y':int(y+10)},1280,720)
        self.assertTrue(self.p.detail);self.assertEqual(self.p.selected,'1')
        display.pointer_action(self.p,self.data,{'action':'back','x':0,'y':0},1280,720)
        self.assertFalse(self.p.detail)
        display.pointer_action(self.p,self.data,{'action':'click','x':1270,'y':int(y)},1280,720)
        self.assertFalse(self.p.detail)

    def test_multiline_wrapping_retains_all_command_text(self):
        command='sudo -n python3 -c "print(123)"\nlong argument without-shortcuts'
        rows=panel_state.wrap_lines([command],12)
        self.assertEqual(''.join(rows),command.replace('\n',''))
        self.assertTrue(all(len(row)<=12 for row in rows))


class PointerTests(unittest.TestCase):
    def test_only_mouse_devices_qualify_and_keyboard_events_are_never_emitted(self):
        ev=(1<<1)|(1<<2);key=1<<272
        self.assertTrue(pointer.pointer_capable(ev,key,3,0))
        self.assertFalse(pointer.pointer_capable(ev,(1<<30),3,0))
        motion=pointer.Motion(640,480)
        self.assertIsNone(motion.event(1,30,1))
        self.assertEqual(motion.event(2,0,5000)['x'],639)
        self.assertEqual(motion.event(1,272,1)['action'],'click')
        self.assertEqual(motion.event(2,8,-1)['action'],'wheel-down')
        self.assertEqual(motion.event(3,0,32767,{0:(0,32767)})['x'],639)


class CliTests(unittest.TestCase):
    def test_named_run_preserves_failure_and_classifies_safe_inner_output(self):
        self.assertTrue(activity.safe_task_output('aguja run --label "Memoria" -- free -h'))
        self.assertFalse(activity.safe_task_output('aguja run --label "Privado" -- python3 -'))
        with patch.object(cli.subprocess,'call',return_value=17),patch.object(activity,'emit') as emit:
            self.assertEqual(cli.run_task(['--label','Tarea','--','false']),17)
            self.assertEqual(emit.call_args_list[-1].args,('command_end','17'))

    def test_doctor_detects_inactive_service_instead_of_false_success(self):
        class Result:
            returncode=1
            stdout='failed'
        with patch.object(cli.os,'geteuid',return_value=0),patch.object(cli,'load'),\
             patch('config.ssh_access',return_value=('', 'default')),\
             patch.object(cli.shutil,'which',return_value='/bin/tool'),\
             patch.object(cli.subprocess,'run',return_value=Result()),\
             patch.object(cli.network,'state',return_value={'connected':True}),\
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.doctor(['--json']),1)
            self.assertFalse(json.loads(out.getvalue())['healthy'])


try:
    from PIL import Image
    HAS_PIL=True
except ImportError:HAS_PIL=False


@unittest.skipUnless(HAS_PIL,'Pillow optional on build host')
class TaskRasterTests(unittest.TestCase):
    def test_cards_detail_and_filters_render_at_all_supported_sizes(self):
        p=panel_state.PanelState()
        data={'commands':[{'id':'a:1','session':'a','title':'Memoria','command':'free -h','started':0,'status':'running'}],
              'events':[{'kind':'output','command_id':'a:1','text':'RAM result'}]}
        for dims in [(320,240),(640,480),(1280,720),(1920,1080)]:
            for detail in [False,True]:
                p.detail=detail
                self.assertEqual(display.render(*dims,{},data,view='commands',control=p).size,dims)


if __name__=='__main__':unittest.main()
