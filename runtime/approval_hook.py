#!/usr/bin/python3
"""Codex PreToolUse hook: a private human gate, not a model-chosen approval.

No stdin/tool values are saved. A missing broker, EOF or timeout denies the task.
The pinned Codex does not support native PreToolUse permissionDecision=ask.
"""
import json
import os
import socket
import sys


def main():
    approved=False
    try:
        data=sys.stdin.buffer.read(65537)
        if len(data)>65536:
            raise ValueError('request too large')
        request=json.loads(data)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(580)
            client.connect(os.environ['AGUJA_APPROVAL_SOCKET'])
            client.sendall(json.dumps(request).encode()+b'\n')
            approved=client.recv(20)==b'approve\n'
    except (OSError,ValueError,KeyError,TypeError):
        pass
    if not approved:
        print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',
            'permissionDecision':'deny','permissionDecisionReason':'LA AGUJA: task was not confirmed by the user.'}}))
    else:
        # An empty successful hook lets this one confirmed call proceed.
        print('{}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
