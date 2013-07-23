
# BEWARE: a blank request (eg. only a newline) signals an end to that whole cilent-server conversation


RELAY_SERVER = ('localhost', 8082)

SERVERS = [
    ('localhost', 8111)
    ,('localhost', 8112)
    ,('localhost', 8113)
    ]

VERBOSE = 1


import socket
import threading

# Read from the sockets, looking for "\n" (one character at a time).
def readLine(s):
    return s.makefile().readline().rstrip("\n")
'''
    ret = ''
    while True:
        c = s.recv(1)
        if c == '\n' or c == '':
            break
        else:
            ret += c
    return ret
'''


def hostAndPortTuple(hostAndPort):
    hostPortList = hostAndPort.split(":")
    return (hostPortList[0], int(hostPortList[1]))

socketsToShutdown = []
def shutdownAllSockets():
    print "Shutting it all down."
    for sock in socketsToShutdown:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        finally:
            pass # don't care about errors; just want to close them all
    exit(0)


class CopyFromSockToSock(threading.Thread):
    def __init__(self, clientSock, serverSock):
        super(CopyFromSockToSock, self).__init__()
        self.clientSock = clientSock
        self.serverSock = serverSock
    def run(self):
        try:
            request = readLine(self.clientSock)
            while (request != ''):
               if (request == 'shutdown relay'):
                   shutdownAllSockets()
               else:
                    self.serverSock.sendall(request + "\n")
                    response = readLine(self.serverSock)
                    self.clientSock.sendall(response + "\n")
                    request = readLine(self.clientSock)
        finally:
            self.clientSock.close()
            self.serverSock.close()

class RouteThroughRelay(threading.Thread):
    def __init__(self, publicHostAndPort, relaySock, serverHostAndPort):
        super(RouteThroughRelay, self).__init__()
        self.publicHostAndPort = publicHostAndPort
        self.serverHostAndPort = serverHostAndPort
        self.relaySock = relaySock
    def run(self):
        socketsToShutdown.append(relaySock)

        # This is the part of the program where you'll want to customize behavior for this server.

        try:
            newClientHostPortStr = readLine(self.relaySock)
            while (newClientHostPortStr != ''):
                if (VERBOSE):
                    print "New client now available at {} going to {}".format(newClientHostPortStr,
                                                                              self.serverHostAndPort)
                newClientHostAndPort = hostAndPortTuple(newClientHostPortStr)
            
                clientRelaySock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                clientRelaySock.connect(newClientHostAndPort)
                socketsToShutdown.append(clientRelaySock)
            
                serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                serverSock.connect(self.serverHostAndPort)
                socketsToShutdown.append(serverSock)
            
                CopyFromSockToSock(clientRelaySock, serverSock).start()

                newClientHostPortStr = readLine(self.relaySock)

        finally:
            pass
#            shutdownAllSockets()


print "To shutdown, connect to any public port and enter: shutdown relay"

# For each server, get a connection to the relay.
for idx, serverHostAndPort in enumerate(SERVERS):
    relaySock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    relaySock.connect(RELAY_SERVER)
    # get the HOST:PORT for this server's public address
    publicHostAndPort = hostAndPortTuple(readLine(relaySock))
    # let's show the public address for this server
    if (VERBOSE):
        print "server {}={} is public at {}".format(idx, serverHostAndPort, publicHostAndPort)
    RouteThroughRelay(publicHostAndPort, relaySock, serverHostAndPort).start()
    