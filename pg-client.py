import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(("localhost", 55559))

try:
    while True:
        line = input("> ")
        if line == "exit":
            break
        try:
            client.send(line.encode("utf-8"))
        except ConnectionError as e:
            print(e)
            print("Disconnecting")
            break
finally:
    client.close()
