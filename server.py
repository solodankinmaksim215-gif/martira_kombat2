#!/usr/bin/env python3
"""МАРТИРА КОМБАТ — статика + API рефералок"""
import json, os, time, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data.json')
REF_REWARD = 5000    # тому, кто пригласил
JOIN_BONUS = 1000    # тому, кто зашёл по ссылке
lock = threading.Lock()

def load():
    try:
        with open(DATA) as f:
            d = json.load(f)
            if 'players' not in d: d = {'players': {}}
            return d
    except Exception:
        return {'players': {}}

def save(d):
    tmp = DATA + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f)
    os.replace(tmp, DATA)

def player(pl, pid):
    return pl.setdefault(pid, {'friends': [], 'pending': 0, 'invitedBy': None, 'ts': time.time()})

class H(SimpleHTTPRequestHandler):
    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/join':
            q = parse_qs(u.query)
            self.api_join((q.get('ref') or [''])[0][:64], (q.get('pid') or [''])[0][:64])
        elif u.path == '/api/me':
            q = parse_qs(u.query)
            self.api_me((q.get('pid') or [''])[0][:64])
        else:
            if u.path == '/':
                self.path = '/index.html'
            super().do_GET()

    def api_join(self, ref, pid):
        if not pid or not ref or pid == ref:
            return self._json({'ok': False, 'reason': 'bad_params'})
        with lock:
            d = load()
            pl = d['players']
            p = player(pl, pid)
            if p.get('invitedBy') is None:
                p['invitedBy'] = ref
                r = player(pl, ref)
                r['friends'].append({'pid': pid, 'ts': time.time()})
                r['pending'] += REF_REWARD
                save(d)
                return self._json({'ok': True, 'bonus': JOIN_BONUS})
            return self._json({'ok': False, 'reason': 'already_invited'})

    def api_me(self, pid):
        if not pid:
            return self._json({'ok': False, 'reason': 'bad_params'})
        with lock:
            d = load()
            pl = d['players']
            p = player(pl, pid)
            pending = p.get('pending', 0)
            p['pending'] = 0
            friends = list(reversed(p.get('friends', [])))[:100]
            count = len(p.get('friends', []))
            save(d)
            self._json({'ok': True, 'pending': pending, 'friends': friends, 'count': count})

    def log_message(self, *a):
        pass

if __name__ == '__main__':
    os.chdir(ROOT)
    port = int(os.environ.get('PORT', 8000))
    print(f'Мартира Комбат API+static on :{port}')
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()
