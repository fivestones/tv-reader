import socket
import threading
import time


def websock_messages():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("localhost", 55557))
    server.listen(1)
    server.setblocking(False)

    
    client = None
    text = ""
    running = True
    while running:

        if client is None:
            try:
                client, address = server.accept()
            except BlockingIOError:
                pass
        else:
            try:
                raw = client.recv(1024)
            except BlockingIOError:
                pass
            else:
                text = raw.decode("utf-8")


        if not text == None:
            print(text)
        text = None
        # time.sleep(0.01)





# websock_messages()

t = threading.Thread(name='websocket', target=websock_messages)
t.start()

time.sleep(6)
print("I'm still working here")