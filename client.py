import time
import paramiko

if __name__ == "__main__":
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect("127.0.0.1", port=2222, username="mist", password="password")
    shell = client.invoke_shell()

    time.sleep(5)
    print(shell.recv(4096))

    shell.send("\x1b[B")
    shell.send("\r")
    time.sleep(5)
    print(shell.recv(4096).decode("utf-8"))

    time.sleep(5)
