"""
Cliente BlackJack (21) — TCP
Python 3  |  input() == raw_input() do Python 2
"""
import socket, json

def main():
    host = input('Host do servidor [localhost]: ').strip() or 'localhost'

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, 5555))
    print(f'Conectado a {host}:5555\n')

    buf = ''
    while True:
        try:
            chunk = sock.recv(4096)
        except OSError:
            break
        if not chunk:
            break

        buf += chunk.decode('utf-8')

        while '\n' in buf:
            line, buf = buf.split('\n', 1)
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            if msg['type'] == 'action':
                # input() em Python 3 == raw_input() em Python 2
                resp = input(msg['msg'])
                sock.sendall((resp + '\n').encode())
            else:
                print(msg.get('msg', ''))

    print('\nFim do jogo. Conexão encerrada.')
    sock.close()

if __name__ == '__main__':
    main()
