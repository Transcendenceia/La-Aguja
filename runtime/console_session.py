#!/usr/bin/python3
"""Local shell with the same non-invasive sanitized trace as SSH."""
import os
import ssh_session

if __name__ == '__main__':
    import console_history
    code = console_history.run(['/usr/bin/python3', '/usr/lib/aguja/console_session.py'])
    if code is not None:
        raise SystemExit(code)
    os.environ['AGUJA_LOCAL_CONSOLE'] = '1'
    os.environ['AGUJA_COCKPIT'] = '1'
    os.environ.pop('SSH_ORIGINAL_COMMAND', None)
    raise SystemExit(ssh_session.main())
