from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
import logging
import random

MIN_PORT = 5057
MAX_PORT = 5070
# Addresses of other physical devices should go here (yet to implement)
EXTERNAL_NETWORKS = []


# Represents a connection (could be client -> server or server -> client)
class NodeProtocol(Protocol):
    def __init__(self, factory, incoming):
        self.id = factory.id
        self.factory = factory
        self.incoming = incoming
        logging.debug(f"[New node protocol]: {self.id}")

    def connectionMade(self):
        logging.info(f"[Connected]: {self.transport.getPeer()}")
        # if self.incoming:
        #     self.connections.append(self)

    def connectionLost(self, reason):
        logging.info(f"[Disconnected]: {self.transport.getPeer()}")

    def dataReceived(self, data):
        logging.debug(f"Data received: {data}")
        self.handleMsg(data)

    def sendMsg(self, msg):
        self.transport.write(msg.encode())

    def handleMsg(self, data):
        self.factory.icn_protocol.handleMsg(data, self)

    def disconnect(self):
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

        endp = TCP4ServerEndpoint(reactor, port)
        endp.listen(self)

        self.part_of_network = False
        self.isolated = True

    def buildProtocol(self, addr):
        protocol = NodeProtocol(self, False)
        protocol.factory = self
        return protocol

    def client(self, port, addr="localhost", announce_msg=None):
        # "Client"
        self.addr = addr
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
            return
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

    def search(self, msg, port_iter=None):
        if port_iter is None:
            ports_to_check = [*range(MIN_PORT, MAX_PORT + 1)]
            random.shuffle(ports_to_check)
            port_iter = iter(ports_to_check)
        try:
            port = next(port_iter)
            if port == self.port:
                port = next(port_iter)
        except StopIteration:
            reactor.callLater(1, self.searchFailed, msg)
            return
        logging.debug(f"Looking on port: {port}")
        if len(self.connections) > 0:
            logging.debug(f"Stopping search")
            return
        d = self.client(port, announce_msg=msg)
        d.addCallback(self.continueSearch, msg, port_iter)

    def continueSearch(self, prot, msg, port_iter):
        reactor.callLater(0.2, self.search, msg, port_iter)

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

    def remove_node_connection(self, node_name):
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
            self.remove_node_connection(node_name)
        if node_name in self.IP_map:
            self.IP_map.pop(node_name)

    def errorHandler(self, e):
        e.trap(ConnectionRefusedError)
