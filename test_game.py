"""
Teste automatizado — dois cenários:
  A) vote_stop=True  → ambos votam N após a 1ª rodada → ranking por votação
  B) vote_stop=False → ambos votam S sempre → jogo até eliminação natural
"""
import subprocess, socket, threading, json, time, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
ADDR = ('localhost', 5555)
SEP  = '─' * 54

def drive_client(name, hs_actions, vote_actions, results, idx):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for _ in range(20):
        try: s.connect(ADDR); break
        except ConnectionRefusedError: time.sleep(0.15)
    else:
        results[idx] = [f'[{name}] ERRO: não conectou']; return

    buf, log, hs_q, vt_q = '', [], list(hs_actions), list(vote_actions)

    while True:
        try: chunk = s.recv(4096)
        except OSError: break
        if not chunk: break
        buf += chunk.decode('utf-8')
        while '\n' in buf:
            line, buf = buf.split('\n', 1)
            line = line.strip()
            if not line: continue
            try: msg = json.loads(line)
            except: continue
            if msg['type'] == 'action':
                prompt = msg['msg'].strip()
                pl     = prompt.lower()
                if 'nome' in pl:
                    resp = name
                elif 'continuar' in pl:
                    resp = vt_q.pop(0) if vt_q else 'S'
                else:
                    resp = hs_q.pop(0) if hs_q else 'S'
                log.append(f'  [{name}] ← {prompt!r}  →  {resp!r}')
                s.sendall((resp + '\n').encode())
            elif msg.get('msg','').strip():
                log.append(msg['msg'])

    s.close()
    results[idx] = log


def run_scenario(label, hs_a, vt_a, hs_b, vt_b, num_players=2):
    print(f'\n{"="*54}')
    print(f'  CENÁRIO: {label}')
    print(f'{"="*54}')

    srv = subprocess.Popen(
        [sys.executable, 'server.py', str(num_players)],
        cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    srv_lines = []
    threading.Thread(target=lambda: [srv_lines.append(l.rstrip()) for l in srv.stdout],
                     daemon=True).start()
    time.sleep(0.8)

    players = [('Ana', hs_a, vt_a), ('Leo', hs_b, vt_b)]
    results = [None] * 2
    threads = [threading.Thread(target=drive_client, args=(*p, results, i))
               for i, p in enumerate(players)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=60)

    srv.terminate(); srv.wait(); time.sleep(0.2)

    print(f'\n{SEP}\n  LOG DO SERVIDOR\n{SEP}')
    for l in srv_lines: print(l)

    for idx, (name, *_) in enumerate(players):
        print(f'\n{SEP}\n  VISÃO DE {name.upper()}\n{SEP}')
        for line in (results[idx] or []): print(line)


# ── Cenário A: empate forçado + ambos votam parar ─────────────────────────────
# (sem hit — quem tiver mais pontos vence; em caso de empate, pote é dividido)
run_scenario(
    label      = 'A — Empate + votação de parada',
    hs_a       = ['S'] * 5,   # Ana sempre para
    vt_a       = ['N'] * 5,   # Ana vota parar
    hs_b       = ['S'] * 5,   # Leo sempre para
    vt_b       = ['N'] * 5,   # Leo vota parar
)

# ── Cenário B: jogo completo até eliminação ───────────────────────────────────
run_scenario(
    label      = 'B — Jogo completo até eliminação',
    hs_a       = ['H', 'S'] + ['S'] * 30,  # Ana pede 1 carta na 1ª rodada
    vt_a       = ['S'] * 30,               # Ana sempre continua
    hs_b       = ['S'] * 30,
    vt_b       = ['S'] * 30,               # Leo sempre continua
)

print(f'\n{"="*54}\n  TODOS OS TESTES CONCLUÍDOS\n{"="*54}')
