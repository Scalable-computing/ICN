from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
import logging
import random

LOCAL = ['localhost', '127.0.0.1']

# PI values
MIN_PORT = 33010
MAX_PORT = 33020
NETWORKS = ["10.35.70.22", "10.35.70.23"]

# Local machine values
# MIN_PORT = 5060
# MAX_PORT = 5070
# NETWORKS = ["localhost", "127.0.0.1"]


# Represents a connection (could be client -> server or server -> client)
class NodeProtocol(Protocol):
    def __init__(self, factory, incoming):
        self.id = factory.id
        self.factory = factory
        self.incoming = incoming
        logging.debug(f"[New node protocol]: {self.id}")

    def connectionMade(self):
        logging.debug(f"[Connected]: {self.transport.getPeer()}")

    def connectionLost(self, reason):
        logging.debug(f"[Disconnected]: {self.transport.getPeer()}")
        self.factory.removeConnection(self.transport.getPeer())

    def dataReceived(self, data):
        logging.debug(f"Data received: {data}")
        self.handleMsg(data)

    def sendMsg(self, msg):
        self.transport.write(msg.encode())

    def handleMsg(self, data):
        self.factory.icn_protocol.handleMsg(data, self)

    def disconnect(self):
        logging.debug(f"[Disconnecting...]: {self.transport.getPeer()}")
        self.transport.loseConnection()


# Factory class used for persistent data since
# protocol instance is created each time connection
# is made
class IPNode(Factory):

    def __init__(self, icnp, node_id, port):
        # "Server"
        self.id = node_id
        self.port = port
        self.connections = {}
        self.IP_map = {}
        self.icn_protocol = icnp
        self.fallback_address = None
        self.fallbacks = {}

        endp = TCP4ServerEndpoint(reactor, port)
        endp.listen(self)

        self.part_of_network = False
        self.isolated = True

        self.addr = "localhost"

    def buildProtocol(self, addr):
        protocol = NodeProtocol(self, False)
        protocol.factory = self
        return protocol

    def client(self, port, addr="localhost", announce_msg=None):
        # "Client"
        try:
            endp = TCP4ClientEndpoint(reactor, addr, port)
            d = connectProtocol(endp, NodeProtocol(self, True))
            d.addCallback(self.confirmConnection, announce_msg)
            d.addErrback(self.errorHandler)
            return d
        except ConnectionRefusedError:
            return d

    def getConnection(self, node_id):
        if node_id in self.connections:
            return self.connections[node_id]
        elif node_id in self.IP_map:
            return None
        else:
            return None

    def clientMsg(self, port, addr, msg):
        try:
            endp = TCP4ClientEndpoint(reactor, addr, port)
            d = connectProtocol(endp, NodeProtocol(self, True))
            d.addCallback(self.confirmMessage, msg)
            d.addErrback(self.errorHandler)
            return d
        except ConnectionRefusedError:
            return d

    def sendMsg(self, msg, node_name, connection=None):
        if node_name is None:
            connection = connection
        else:
            connection = self.getConnection(node_name)
        if connection is None:
            logging.warning(f"No connection found or established with {node_name}")
            try:
                addr, port = self.IP_map[node_name].split(':')
                port = int(port)
                self.clientMsg(port, addr, msg)
            except Exception as e:
                logging.error(repr(e))
                logging.warning(f"Could not connect to {node_name}")
            finally:
                return
        connection.sendMsg(msg)

    def search(self, msg, port_iter=None, addr="localhost", addr_iter=None):
        if port_iter is None:
            ports_to_check = [*range(MIN_PORT, MAX_PORT + 1)]
            random.shuffle(ports_to_check)
            port_iter = iter(ports_to_check)
        if addr_iter is None:
            networks_to_check = NETWORKS
            random.shuffle(networks_to_check)
            addr_iter = iter(networks_to_check)
            addr = next(addr_iter)
        try:
            port = next(port_iter)
            if port == self.port:
                port = next(port_iter)
        except StopIteration:
            try:
                addr = next(addr_iter)
                self.search(msg, None, addr, addr_iter)
                return
            except StopIteration:
                reactor.callLater(1, self.searchFailed, msg)
                return
        if len(self.connections) > 0:
            logging.debug(f"Stopping search")
            return
        logging.debug(f"Looking on: {addr}:{port}")
        d = self.client(port, addr=addr, announce_msg=msg)
        d.addCallback(self.continueSearch, msg, port_iter, addr, addr_iter)

    def continueSearch(self, prot, msg, port_iter, addr, addr_iter):
        reactor.callLater(0.1, self.search, msg, port_iter, addr, addr_iter)

    def searchFailed(self, msg):
        if len(self.connections) > 0:
            return
        elif self.isolated:
            logging.warning("No nodes found on network.")
            self.part_of_network = True
            return
        else:
            logging.warning(f"Search failed.")
            self.isolated = True
            reactor.callLater(5, self.search, msg)

    def addNodeConnection(self, node_name, source):
        self.connections[node_name] = source
        self.part_of_network = True

    def addNodeAddr(self, node_name, port, host, source=None):
        if node_name == self.id:
            return
        if node_name not in self.IP_map:
            logging.debug(f"{node_name} not in IP map, adding...")
            if source is not None:
                host = source.transport.getPeer().host
            addr = f"{host}:{port}"
            self.IP_map[node_name] = addr

    def getPort(self):
        return str(self.port)

    def getPeerAddr(self, node_name):
        if node_name == self.id:
            return f"{self.addr}:{self.port}"
        if node_name not in self.IP_map:
            return None
        else:
            return self.IP_map[node_name]

    def removeNodeConnection(self, node_name):
        p = self.connections.pop(node_name)
        p.disconnect()

    def confirmConnection(self, prot, msg):
        self.sendMsg(msg, None, prot)
        return prot

    def confirmMessage(self, prot, msg):
        prot.sendMsg(msg)
        return prot

    def verifyPeer(self, node_name):
        if node_name in self.IP_map and node_name not in self.icn_protocol.node.peers:
            self.removePeer(node_name)

    def removePeer(self, node_name):
        if node_name in self.connections:
            self.removeNodeConnection(node_name)
        # if node_name in self.IP_map:
        #     self.IP_map.pop(node_name)
        self.icn_protocol.node.removePeer(node_name)

    def removeConnection(self, peer):
        addr = f"{peer.host}:{peer.port}"
        for k, p in self.IP_map.items():
            if addr == p:
                self.removePeer(k)
                self.fallbackDisconnect(k, addr)
                break

    def getFallback(self):
        return self.fallback_address

    def setFallback(self, node_name, addr, source, port):
        if self.fallback_address is None:
            if addr is not None and port is not None:
                host, p, n = addr.split(':')
                # if host in LOCAL:
                host = source.transport.getPeer().host
            elif port is not None:
                host = source.transport.getPeer().host
            addr = f"{host}:{port}:{node_name}"
            self.fallback_address = addr
            for p in self.icn_protocol.node.peers:
                if p == node_name:
                    continue
                else:
                    self.icn_protocol.sendFallback(p, addr)
            return self.fallback_address
        else:
            return None

    def updateFallback(self, node_name, addr):
        self.fallbacks[node_name] = addr

    def fallbackDisconnect(self, node_name, addr):
        host, port = addr.split(':')
        addr = f"{host}:{port}:{node_name}"
        if addr == self.fallback_address:
            self.fallback_address = None
        if node_name in self.fallbacks:
            logging.debug(f"{node_name} found in fallback table of {self.id}")
            f = self.fallbacks.pop(node_name)
            msg = self.icn_protocol.getAnnounce()
            host, port, n = f.split(':')
            if n == self.id:
                return
            self.addNodeAddr(n, port, host)
            self.sendMsg(msg, n)

    def errorHandler(self, e):
        e.trap(ConnectionRefusedError)
