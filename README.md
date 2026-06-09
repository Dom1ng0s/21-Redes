# BlackJack (21) — Multiplayer via TCP

Trabalho de redes — implementação de um jogo de BlackJack multiplayer sobre sockets TCP crus em Python 3, com threads e protocolo JSON próprio.

## Funcionalidades

- **2 a 4 jogadores** em rede local (ou na mesma máquina)
- Mãos **privadas** — cada jogador vê apenas as próprias cartas
- Aposta fixa de **100 fichas** por rodada; início com **500 fichas**
- **Dealer rotativo** entre os jogadores ativos
- **Votação de parada** unânime ao final de cada rodada
- **Eliminação** automática de quem não tem fichas suficientes para apostar
- **Ranking final** exibido para todos ao encerrar a partida
- Servidor com **cores ANSI** por jogador para facilitar o acompanhamento

## Requisitos

- Python 3.6+
- Nenhuma dependência externa — apenas a biblioteca padrão

## Como executar

**1. Inicie o servidor** (aceita 2, 3 ou 4 jogadores; padrão: 4):

```bash
python server.py          # 4 jogadores
python server.py 2        # 2 jogadores
python server.py 3        # 3 jogadores
```

O servidor escuta em `0.0.0.0:5555` e bloqueia até que todos os jogadores se conectem.

**2. Conecte os clientes** (um por terminal, na mesma máquina ou em hosts diferentes):

```bash
python client.py
# Host do servidor [localhost]:  ← pressione Enter para localhost ou digite o IP
```

Repita para cada jogador. O jogo começa assim que o último jogador conectar.

## Como jogar

Após conectar, cada jogador informa seu nome. Quando todos estiverem prontos, as rodadas começam:

- Em cada turno, o jogador escolhe:
  - `H` — **Hit**: pedir mais uma carta
  - `S` — **Stand**: parar com a mão atual
- Quem ultrapassar **21** pontos está **fora** da rodada (bust)
- O jogador com o maior valor sem estourar **vence o pote** da rodada
- Em caso de **empate**, o pote é dividido igualmente
- Se **todos** estourarem, as apostas são devolvidas
- Ao final de cada rodada, os jogadores ativos votam para continuar (`S`) ou parar (`N`); o jogo encerra apenas com **unanimidade** para parar
- Jogador com fichas abaixo da aposta mínima (100) é **eliminado**; passa a assistir as rodadas seguintes
- O jogo termina quando restar **1 ou menos** jogadores ativos, ou por votação unânime

## Arquitetura

```
server.py
  main()         — aceita N conexões TCP, cria 1 thread por jogador
  get_name()     — thread: coleta nome e aguarda na Barrier
  game()         — loop sequencial de rodadas (thread principal)
  play_round()   — distribui cartas, gerencia turnos e resultado
  stop_vote()    — coleta voto de cada jogador ativo
  show_ranking() — exibe classificação final

client.py
  main()         — loop de recv; chama input() apenas para mensagens tipo "action"
```

### Protocolo

Mensagens JSON delimitadas por `\n` sobre TCP:

| Tipo | Direção | Descrição |
|---|---|---|
| `{"type": "info",   "msg": "..."}` | servidor → cliente | Exibe texto na tela |
| `{"type": "action", "msg": "..."}` | servidor → cliente | Solicita entrada do usuário |

### Modelo de concorrência

Threads são usadas **apenas** na fase de coleta de nomes: cada thread chama `threading.Barrier(N).wait()` e encerra. Depois que todas fazem join, o loop do jogo roda de forma **totalmente sequencial** na thread principal — sem condições de corrida.

## Restrições do trabalho

| Requisito | Implementação |
|---|---|
| Sem WebSockets | `socket.socket(AF_INET, SOCK_STREAM)` |
| Threads obrigatórias | `threading.Thread` + `threading.Barrier` |
| N jogadores | configurável via argumento (2–4) |
