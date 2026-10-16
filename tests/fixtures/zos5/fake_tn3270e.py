#!/usr/bin/env python3
"""Local fake TN3270E host (localhost only) to see how x3270 4.5 traces a mid-session Trace(On): negotiates TN3270E
(RFC 2355, no functions), sends READY, waits for the go file, then: switch 7E C3, query, reads the reply, a full
screen F1, waits for one ENTER, a partial, line READY; then idles."""
import os
import socket
import sys
import time

IAC, SB, SE, DO, WILL, EOR = 255, 250, 240, 253, 251, 239
TN3270E = 40
port, go = int(sys.argv[1]), sys.argv[2]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', port))
s.listen(1)
c, _ = s.accept()
c.settimeout(20)
seq = [0]


def rd():
    return c.recv(65536)


def send_rec(p, dt=0):
    c.sendall(bytes([dt, 0, 0]) + seq[0].to_bytes(2, 'big') + p.replace(b'\xff', b'\xff\xff') + bytes([IAC, EOR]))
    seq[0] += 1


c.sendall(bytes([IAC, DO, TN3270E]))
print('got', rd().hex(), flush=True)                                       # WILL TN3270E
c.sendall(bytes([IAC, SB, TN3270E, 8, 2, IAC, SE]))                        # SEND DEVICE-TYPE
d = rd()
print('devtype req', d, flush=True)
term = d[d.index(bytes([2, 7])) + 2:].split(bytes([IAC]))[0].split(b'\x01')[0]   # DEVICE-TYPE REQUEST <type>
c.sendall(bytes([IAC, SB, TN3270E, 2, 4]) + term + bytes([1]) + b'LUFAKE01' + bytes([IAC, SE]))
d = rd()
print('functions', d.hex(), flush=True)
c.sendall(bytes([IAC, SB, TN3270E, 3, 4, IAC, SE]))                        # FUNCTIONS IS (none)
time.sleep(0.5)
send_rec(bytes.fromhex('F5C3114040') + 'READY'.encode('cp037'))
while not os.path.exists(go):
    time.sleep(0.2)
send_rec(bytes.fromhex('7EC3'))
send_rec(bytes.fromhex('F3000501FF02'))
print('reply', rd().hex(), flush=True)
send_rec(bytes.fromhex('F1C31140403C404000') + b'\x11\x40\x40' + 'P A C - M A N'.encode('cp037') + b'\x13')
print('enter', rd().hex(), flush=True)
send_rec(bytes.fromhex('F1C31140C1') + 'MOVED'.encode('cp037'))
send_rec(bytes.fromhex('F1C3114040') + 'READY'.encode('cp037'))
time.sleep(30)
