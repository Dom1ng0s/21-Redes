"""
Servidor BlackJack (21) — TCP, Threads
Aposta fixa: 100 fichas | Início: 500 fichas
Informações privadas por jogador; servidor vê tudo (com cores por jogador).
Uso: python server.py [num_jogadores]  (padrão: 4, mínimo: 2)
"""
import socket, threading, json, random, sys

N     = int(sys.argv[1]) if len(sys.argv) > 1 else 4
BET   = 100
START = 500

if not 2 <= N <= 4:
    sys.exit('Número de jogadores deve ser 2, 3 ou 4.')

# ── cores ANSI — apenas no terminal do servidor ───────────────────────────────
_CLR = ['\033[96m', '\033[92m', '\033[93m', '\033[95m']  # ciano verde amarelo magenta
RST  = '\033[0m'
BLD  = '\033[1m'

def pc(idx, text):
    """Colore texto com a cor exclusiva do jogador idx."""
    return f'{_CLR[idx % 4]}{text}{RST}'

def log(msg): print(msg)

# ── helpers ───────────────────────────────────────────────────────────────────

def hand_val(hand):
    v = sum(11 if r == 'A' else 10 if r in ('J','Q','K') else int(r) for r,_ in hand)
    a = sum(1 for r,_ in hand if r == 'A')
    while v > 21 and a: v -= 10; a -= 1
    return v

def fmt(hand): return ' '.join(r+s for r,s in hand)

def make_deck():
    d = [(r,s) for s in ('♠','♥','♦','♣')
         for r in ['2','3','4','5','6','7','8','9','10','J','Q','K','A']]
    random.shuffle(d); return d

def send(sock, msg):
    try: sock.sendall((json.dumps(msg)+'\n').encode())
    except: pass

def recv(sock):
    buf = b''
    while True:
        c = sock.recv(1)
        if not c or c == b'\n': break
        buf += c
    return buf.decode().strip()

# ── thread por jogador ────────────────────────────────────────────────────────

def get_name(sock, names, idx, barrier):
    send(sock, {'type':'action', 'msg':'Seu nome: '})
    names[idx] = recv(sock) or f'Jogador{idx+1}'
    send(sock, {'type':'info', 'msg':f'Bem-vindo, {names[idx]}! Aguardando os demais...'})
    barrier.wait()

# ── uma rodada ────────────────────────────────────────────────────────────────

def play_round(rnd, active, socks, names, balances, dealer_idx, cn):
    sep = '─' * 42
    spectators = [i for i in range(len(socks)) if i not in active]

    # Cabeçalho da rodada — ativos jogam, eliminados assistem
    for i in range(len(socks)):
        if i in active:
            send(socks[i], {'type':'info',
                'msg': f'\n{sep}\n Rodada {rnd}  |  Dealer: {names[dealer_idx]}\n'
                       f' Aposta fixa: {BET}  |  Suas fichas: {balances[i]}\n{sep}'})
        else:
            send(socks[i], {'type':'info',
                'msg': f'\n{sep}\n Rodada {rnd}  (você está eliminado — assistindo)\n{sep}'})

    log(f'\n{sep}\n {BLD}RODADA {rnd}{RST} | Dealer: {cn[dealer_idx]}')
    log(' Fichas: ' + ' | '.join(f'{cn[i]}={balances[i]}' for i in range(len(socks))))

    for i in active: balances[i] -= BET

    # Distribui 2 cartas — cada jogador vê só as suas
    deck = make_deck()
    hands = {i: [] for i in active}
    for _ in range(2):
        for i in active: hands[i].append(deck.pop())

    log(' Cartas iniciais:')
    for i in active: log(f'   {cn[i]}: {fmt(hands[i])} [{hand_val(hands[i])}]')

    for i in active:
        send(socks[i], {'type':'info',
            'msg': f'Suas cartas: {fmt(hands[i])} [{hand_val(hands[i])}]'})

    # Espectadores veem todas as mãos iniciais
    if spectators:
        spec_hands = '\n'.join(
            f'  {names[i]}: {fmt(hands[i])} [{hand_val(hands[i])}]' for i in active)
        for s in spectators:
            send(socks[s], {'type':'info', 'msg': f'Cartas iniciais:\n{spec_hands}'})

    busted = {i: False for i in active}

    # Turno: esquerda do dealer → ... → dealer
    dp    = active.index(dealer_idx)
    order = active[dp+1:] + active[:dp+1]

    for i in order:
        for j in range(len(socks)):
            send(socks[j], {'type':'info', 'msg': f'\n▶ Vez de {names[i]}'})

        while True:
            v = hand_val(hands[i])
            send(socks[i], {'type':'action',
                'msg': f'  Mão: {fmt(hands[i])} [{v}]\n  [H]it ou [S]tand? '})
            act = recv(socks[i]).upper()

            if act not in ('H','S'):
                send(socks[i], {'type':'info', 'msg': '  Inválido. Use H ou S.'})
                continue

            if act == 'H':
                card = deck.pop()
                hands[i].append(card)
                v = hand_val(hands[i])
                # Só o jogador vê a carta recebida; espectadores veem tudo (visão do servidor)
                send(socks[i], {'type':'info',
                    'msg': f'  Carta: {card[0]+card[1]}  →  Mão: {fmt(hands[i])} [{v}]'})
                for j in active:
                    if j != i: send(socks[j], {'type':'info', 'msg': f'  {names[i]} pediu carta.'})
                for s in spectators:
                    send(socks[s], {'type':'info',
                        'msg': f'  {names[i]} pediu: {card[0]+card[1]}  →  {fmt(hands[i])} [{v}]'})
                log(f'   {cn[i]} hit: {card[0]+card[1]} → [{v}]')

                if v > 21:
                    busted[i] = True
                    send(socks[i], {'type':'info', 'msg': '  Você ESTOUROU!'})
                    for j in active:
                        if j != i: send(socks[j], {'type':'info', 'msg': f'  {names[i]} ESTOUROU!'})
                    for s in spectators:
                        send(socks[s], {'type':'info', 'msg': f'  {names[i]} ESTOUROU!'})
                    log(f'   {cn[i]} {BLD}BUST{RST}')
                    break
                if v == 21:
                    send(socks[i], {'type':'info', 'msg': '  21! Perfeito.'})
                    for j in active:
                        if j != i: send(socks[j], {'type':'info', 'msg': f'  {names[i]} tem 21!'})
                    for s in spectators:
                        send(socks[s], {'type':'info', 'msg': f'  {names[i]} tem 21!'})
                    break
            else:
                send(socks[i], {'type':'info', 'msg': '  Você parou.'})
                for j in active:
                    if j != i: send(socks[j], {'type':'info', 'msg': f'  {names[i]} parou.'})
                for s in spectators:
                    send(socks[s], {'type':'info',
                        'msg': f'  {names[i]} parou com {fmt(hands[i])} [{hand_val(hands[i])}].'})
                log(f'   {cn[i]} stand [{hand_val(hands[i])}]')
                break

    # ── resultado da rodada ───────────────────────────────────────────────────
    pot    = BET * len(active)
    scores = [(hand_val(hands[i]), i) for i in active if not busted[i]]
    log(' Placar:')
    for i in active:
        log(f'   {cn[i]}: {fmt(hands[i])} = {"BUST" if busted[i] else hand_val(hands[i])}')

    if spectators:
        placar = 'Placar:\n' + '\n'.join(
            f'  {names[i]}: {fmt(hands[i])} = {"BUST" if busted[i] else hand_val(hands[i])}'
            for i in active)
        for s in spectators:
            send(socks[s], {'type':'info', 'msg': placar})

    if not scores:
        log(f' {BLD}TODOS ESTOURARAM{RST} — apostas devolvidas.')
        for i in active:
            balances[i] += BET
            send(socks[i], {'type':'info',
                'msg': f'\nTodos estouraram! Aposta devolvida.\nSuas fichas: {balances[i]}'})
        for s in spectators:
            send(socks[s], {'type':'info', 'msg': '\nTodos estouraram! Apostas devolvidas.'})
        return

    best    = max(v for v,_ in scores)
    winners = [i for v,i in scores if v == best]
    share   = pot // len(winners)
    remainder = pot % len(winners)
    received = {}
    for idx, w in enumerate(winners):
        received[w] = share + (1 if idx < remainder else 0)
        balances[w] += received[w]
    win_str = ', '.join(names[i] for i in winners)

    if len(winners) > 1:
        # ── empate ────────────────────────────────────────────────────────────
        log(f' {BLD}EMPATE{RST}: {" e ".join(cn[i] for i in winners)} '
            f'[{best} pts] | pote {pot} ÷ {len(winners)} = {share} cada')
        for j in active:
            if j in winners:
                others = ', '.join(names[m] for m in winners if m != j)
                send(socks[j], {'type':'info',
                    'msg': f'\n⚖  EMPATE com {others}!'
                           f'\n   Pote dividido — você recebeu {received[j]} fichas.'
                           f'\n   Suas fichas: {balances[j]}'})
            else:
                send(socks[j], {'type':'info',
                    'msg': f'\n⚖  Empate entre {win_str}. Suas fichas: {balances[j]}'})
        for s in spectators:
            send(socks[s], {'type':'info',
                'msg': f'\n⚖  Empate entre {win_str} [{best} pts]. Pote: {pot}.'})
    else:
        # ── vitória única ─────────────────────────────────────────────────────
        log(f' Vencedor: {cn[winners[0]]} [{best}] | pote {pot}')
        for j in active:
            if j in winners:
                send(socks[j], {'type':'info',
                    'msg': f'\nVocê VENCEU a rodada! Suas fichas: {balances[j]}'})
            else:
                send(socks[j], {'type':'info',
                    'msg': f'\nRodada encerrada. Venceu: {win_str}. Suas fichas: {balances[j]}'})
        for s in spectators:
            send(socks[s], {'type':'info',
                'msg': f'\nRodada encerrada. Venceu: {win_str} [{best}]. Pote: {pot}.'})

    # Notifica recém-eliminados
    for i in active:
        if balances[i] < BET:
            send(socks[i], {'type':'info',
                'msg': f'\nVocê foi ELIMINADO! Fichas: {balances[i]} (mínimo: {BET}).'})
            log(f' {cn[i]} {BLD}ELIMINADO{RST} ({balances[i]} fichas)')

# ── votação de parada ─────────────────────────────────────────────────────────

def stop_vote(active, socks, names, cn):
    """Pergunta a cada ativo se quer parar. Retorna True somente se unanimidade."""
    spectators = [i for i in range(len(socks)) if i not in active]
    log(f'\n {BLD}Votação de parada:{RST}')
    for s in spectators:
        send(socks[s], {'type':'info', 'msg': '\nVotação de parada em andamento...'})
    stops = 0
    for i in active:
        while True:
            send(socks[i], {'type':'action', 'msg':'\nContinuar jogando? [S]im / [N]ão: '})
            v = recv(socks[i]).upper()
            if v in ('S','N'): break
            send(socks[i], {'type':'info', 'msg':'Use S ou N.'})
        label = 'quer PARAR' if v == 'N' else 'quer CONTINUAR'
        log(f'   {cn[i]}: {label}')
        for j in active:
            if j != i:
                send(socks[j], {'type':'info', 'msg': f'  {names[i]} {label.lower()}.'})
        for s in spectators:
            send(socks[s], {'type':'info', 'msg': f'  {names[i]} {label.lower()}.'})
        if v == 'N': stops += 1
    return stops == len(active)

# ── ranking ───────────────────────────────────────────────────────────────────

def show_ranking(socks, names, balances, rnd, reason, cn):
    sep    = '─' * 42
    order  = sorted(range(len(names)), key=lambda i: balances[i], reverse=True)
    medals = ['★', '✦', '◆', '◇']

    # Log do servidor (com cores)
    log(f'\n{sep}\n {BLD}RANKING FINAL{RST}  ({rnd} rodada(s) — {reason})\n{sep}')
    for pos, i in enumerate(order, 1):
        m = medals[pos-1] if pos <= 4 else ' '
        s = '  (eliminado)' if balances[i] < BET else ''
        log(f'  {m} #{pos}  {cn[i]}: {balances[i]} fichas{s}')
    log(sep)

    # Mensagem para clientes (sem ANSI)
    lines = [f'\n{sep}', f' RANKING FINAL  ({rnd} rodada(s) — {reason})', sep]
    for pos, i in enumerate(order, 1):
        m = medals[pos-1] if pos <= 4 else ' '
        s = '  (eliminado)' if balances[i] < BET else ''
        lines.append(f'  {m} #{pos}  {names[i]:<14} {balances[i]:>6} fichas{s}')
    lines.append(sep)
    msg = '\n'.join(lines)
    for sock in socks: send(sock, {'type':'info', 'msg': msg})

# ── loop do jogo ──────────────────────────────────────────────────────────────

def game(socks, names):
    cn         = [pc(i, names[i]) for i in range(len(names))]
    balances   = [START] * len(socks)
    dealer_idx = 0
    rnd        = 0
    reason     = 'eliminação'
    sep        = '─' * 42

    intro = (f'\n{sep}\n    B L A C K J A C K  (21)\n{sep}\n'
             f'Jogadores: {", ".join(names)}\n'
             f'Aposta fixa: {BET} fichas  |  Fichas iniciais: {START}')
    for s in socks: send(s, {'type':'info', 'msg': intro})
    log(f'\n{sep}\n {BLD}B L A C K J A C K{RST}\n{sep}')
    log('Jogadores: ' + '  '.join(cn))

    while True:
        active = [i for i in range(len(socks)) if balances[i] >= BET]
        if len(active) <= 1:
            break
        rnd += 1
        play_round(rnd, active, socks, names, balances, dealer_idx, cn)

        new_active = [i for i in range(len(socks)) if balances[i] >= BET]

        # Rotaciona dealer entre os jogadores ainda ativos
        after      = [i for i in new_active if i > dealer_idx]
        dealer_idx = after[0] if after else (new_active[0] if new_active else dealer_idx)

        # Votação — só se o jogo pode continuar (2+ ativos)
        if len(new_active) > 1 and stop_vote(new_active, socks, names, cn):
            log(f' {BLD}Unanimidade: todos votaram PARAR.{RST}')
            reason = 'votação unânime'
            break

    show_ranking(socks, names, balances, rnd, reason, cn)

# ── entrada ───────────────────────────────────────────────────────────────────

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 5555))
    srv.listen(N)
    log(f'[Servidor] Aguardando {N} jogadores na porta 5555...')

    socks, names = [], [None] * N
    barrier = threading.Barrier(N)
    threads = []

    for i in range(N):
        conn, addr = srv.accept()
        socks.append(conn)
        log(f'  [{i+1}/{N}] Conexão: {addr}')
        t = threading.Thread(target=get_name, args=(conn,names,i,barrier), daemon=True)
        t.start(); threads.append(t)

    for t in threads: t.join()
    log('  Todos prontos: ' + '  '.join(pc(i, names[i]) for i in range(len(names))))
    log('  Iniciando partida...')

    game(socks, names)

    for s in socks: s.close()
    srv.close()
    log('[Servidor] Encerrado.')

if __name__ == '__main__':
    main()
