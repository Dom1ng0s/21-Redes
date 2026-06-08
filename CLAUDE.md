# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Multiplayer Blackjack (21) over a local network — university networks assignment. Two-file Python 3 implementation: `server.py` + `client.py`.

## Running

Start the server first, then connect 4 clients (in separate terminals or machines):

```bash
# Terminal 1
python server.py

# Terminals 2–5 (on same or remote host)
python client.py
```

The server listens on `0.0.0.0:5555`. The client prompts for the host (`localhost` by default).

## Architecture

```
server.py
  main()          — accepts 4 TCP connections sequentially, spawns one Thread per connection
  get_name()      — thread function: prompts for name, blocks on threading.Barrier(4)
  game()          — sequential game loop run by main thread after all threads join

client.py
  main()          — single-threaded recv loop; calls input() only when server sends type=action
```

**Protocol:** newline-delimited JSON over TCP.  
- `{"type": "info",   "msg": "..."}` — server→all clients, client prints it  
- `{"type": "action", "msg": "..."}` — server→one client, client calls `input()` and sends reply

**Concurrency model:** Threads are used *only* during the name-collection phase — each of the 4 threads calls `barrier.wait()` and exits. After all threads join, the game runs fully sequential on the main thread (no shared-state issues during play).

**Turn order:** dealer = player 0 (first to connect); play order is 1 → 2 → 3 → 0.

## Constraints (assignment rules)

- **No WebSockets** — raw `socket.socket(AF_INET, SOCK_STREAM)` only.
- **Threads mandatory** — `threading.Thread` + `threading.Barrier`.
- **Exactly 4 players** — server blocks until all 4 connect.
- `input()` is the Python 3 equivalent of Python 2's `raw_input()`.
