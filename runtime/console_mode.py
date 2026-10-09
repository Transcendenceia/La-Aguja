#!/usr/bin/python3
"""Switch only the caller-owned visible VT; needed after a local PTY relay.

A PTY child cannot issue privileged VT ioctls despite owning /dev/tty1. Full
sudo already belongs to the owner. This helper never opens a disk or reads auth.
"""
import fcntl
import os
from pathlib import Path
import re
import sys


def main(args):
    if len(args)!=2 or os.geteuid()!=0 or not re.fullmatch(r'/dev/tty[1-9][0-9]*',args[0]) or args[1] not in ('0','1'):
        return 1
    target=Path(args[0])
    if Path('/sys/class/tty/tty0/active').read_text().strip()!=target.name:
        return 1
    if 'SUDO_UID' in os.environ and target.stat().st_uid!=int(os.environ['SUDO_UID']):
        return 1
    fd=os.open(target,os.O_RDWR|os.O_NOCTTY)
    try:fcntl.ioctl(fd,0x4B3A,int(args[1]))
    finally:os.close(fd)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main(sys.argv[1:]))
    except (OSError,ValueError):raise SystemExit(1)
