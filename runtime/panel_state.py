"""Pure, local-only cockpit selection/filter state; never executes commands."""
VIEWS = ('help', 'commands', 'activity', 'processes')


def wrap_lines(lines, columns):
    """Hard-wrap every logical line, preserving spaces, newlines and long argv."""
    columns = max(1, int(columns))
    return [line[start:start+columns] for value in lines for line in str(value).expandtabs(4).split('\n')
            for start in range(0, max(1, len(line)), columns)]


def command_window(commands, selected, capacity):
    index = next((i for i,c in enumerate(commands) if c.get('id')==selected), len(commands)-1)
    start = max(0, min(index-capacity//2, len(commands)-capacity))
    return commands[start:start+capacity]


def visible(data, technical=False, session=None, failures=False):
    def include(row):
        return (technical or not row.get('technical')) and (not session or row.get('session', row.get('id')) == session)
    result = dict(data)
    for key in ('commands', 'events', 'processes'):
        result[key] = [r for r in data.get(key, []) if include(r)]
    result['sessions'] = [r for r in data.get('sessions', []) if (technical or not r.get('probe')) and (not session or r.get('id') == session)]
    if failures:
        result['commands'] = [c for c in result['commands'] if c.get('status') in ('error', 'cancelled', 'disconnected')]
    result['technical_count'] = sum(bool(c.get('technical')) for c in data.get('commands', []))
    return result


class PanelState:
    def __init__(self):
        self.view = 'help'
        self.technical = self.failures = self.detail = False
        self.session = self.selected = None
        self.scroll = 0
        self.scroll_limit = 0

    def bound_scroll(self, total, capacity):
        self.scroll_limit = max(0, total-max(1,capacity))
        self.scroll = max(0, min(self.scroll, self.scroll_limit))

    def select(self, command_id, expand=False):
        self.selected = command_id
        self.detail = expand
        self.scroll = 0

    def data(self, snapshot):
        return visible(snapshot, self.technical, self.session, self.failures)

    def selected_command(self, data):
        commands = data.get('commands', [])
        return next((c for c in commands if c.get('id') == self.selected), commands[-1] if commands else None)

    def key(self, key, snapshot):
        data = self.data(snapshot)
        if key == 'tab':
            self.view = VIEWS[(VIEWS.index(self.view) + 1) % len(VIEWS)]
            self.detail = False
            self.scroll = 0
        elif key == 'sessions':
            ids = list(dict.fromkeys(c['session'] for c in visible(snapshot, self.technical).get('commands', [])))
            options = [None] + ids
            self.session = options[(options.index(self.session) + 1) % len(options)] if self.session in options else None
            self.selected = None
        elif key in ('technical', 'failures'):
            setattr(self, key, not getattr(self, key))
            self.selected = None
        elif key == 'live':
            self.scroll = 0
            self.selected = None
            self.detail = False
        elif key == 'detail' and self.view == 'commands':
            chosen = self.selected_command(data)
            if chosen:self.selected = chosen['id']
            self.detail = not self.detail
            self.scroll = 0
        elif key == 'back':
            self.detail = False
        elif key in ('up', 'down') and self.detail:
            self.scroll = max(0,min(self.scroll_limit,self.scroll+(-1 if key=='up' else 1)))
        elif key in ('up', 'down', 'previous', 'next') and self.view == 'commands':
            commands = data.get('commands', [])
            if commands:
                current = self.selected_command(data)
                index = commands.index(current)
                index = max(0, min(len(commands)-1, index+(-1 if key in ('up','previous') else 1)))
                self.selected = commands[index]['id']
                self.scroll = 0
        elif key == 'pageup':
            if self.view == 'commands' and not self.detail:
                for _ in range(5):self.key('up',snapshot)
            else:
                self.scroll = max(0,self.scroll-10) if self.detail else min(2000,self.scroll+10)
        elif key == 'pagedown':
            if self.view == 'commands' and not self.detail:
                for _ in range(5):self.key('down',snapshot)
            else:
                self.scroll = min(self.scroll_limit,self.scroll+10) if self.detail else max(0,self.scroll-10)
        elif key == 'home':
            if self.detail:self.scroll = 0
            elif data.get('commands'):self.select(data['commands'][0]['id'])
        elif key == 'end' and self.detail:
            self.scroll = self.scroll_limit


def command_duration(command, now):
    try:
        seconds = max(0, float(command.get('duration', now-float(command.get('started', now)))))
    except (ValueError, TypeError):
        seconds = 0
    return f'{int(seconds)//60}:{int(seconds)%60:02d}'
