import socket
import threading
import logging

import game

# logging setting
logging.basicConfig(level=logging.DEBUG)

# server setting
HOST = 'localhost'
PORT = 12346
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(10)
logging.info('server[{}] listening on port {}'.format(HOST, PORT))

# game related init
game.GameRoomManager().init_instance()

# Main
try:
    while True:
        client, addr = s.accept()                   # get one connection
        logging.debug('connected from {}'.format(addr))
        
        socket_client = game.Player(client, addr)
        thread_name = 'client#{}'.format(addr[1])
        socket_task = threading.Thread(target=socket_client.on_connect, name=thread_name)
        socket_task.start()
finally:
    s.close()
