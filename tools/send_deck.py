#!/usr/bin/env python3
"""Inject optional RAKF credentials in memory and send an ASCII card deck."""
import os
from pathlib import Path
import re
import socket
import sys

text = Path(sys.argv[1]).read_text(encoding='ascii')
user = os.environ.get('TK4_USER', '')
password = os.environ.get('TK4_PASSWORD', '')
if bool(user) != bool(password):
    raise SystemExit('Set both TK4_USER and TK4_PASSWORD, or neither')
if user:
    if not re.fullmatch(r'[A-Z@#$][A-Z0-9@#$]{0,7}', user):
        raise SystemExit('Invalid TK4_USER')
    if not re.fullmatch(r'[A-Z0-9@#$]{1,8}', password):
        raise SystemExit('Password must be 1-8 uppercase JCL-safe characters')
    lines = text.splitlines()
    end = next(i for i in range(1, len(lines)) if not lines[i-1].endswith(','))
    lines[end-1] += ','
    lines.insert(end, f'//             USER={user},PASSWORD={password}')
    text = '\n'.join(lines) + '\n'
try:
    with socket.create_connection((os.environ['TK4_HOST'], int(os.environ['TK4_RDR_PORT'])), timeout=10) as connection:
        connection.sendall(text.encode('ascii'))
        connection.shutdown(socket.SHUT_WR)
except (OSError, ValueError) as exc:
    raise SystemExit(f'Submission failed: {exc}')
