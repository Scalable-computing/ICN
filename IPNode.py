from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
import logging

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
        self.waiting = []
        self.connections = {}
        self.IP_map = {}
        self.icn_protocol = icnp

        endp = TCP4ServerEndpoint(reactor, port)
        endp.listen(self)

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

    def sendClMsg(self, prot, mn):
        msg, node = mn
        self.connections[node] = prot
        try:
            self.waiting.pop()
        except Exception as e:
            logging.error("No matching connection:", e)
        prot.sendMsg(msg)

    def getConnection(self, node_id):
        if node_id in self.connections:
            return self.connections[node_id]
        elif node_id in self.IP_map:
            return
        else:
            return None

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
            except Exception as e:
                logging.error(repr(e))
                logging.warning(f"Could not connect to {node_name}")
            finally:
                return
        connection.sendMsg(msg)

    def update_IP_map(self, ip_map):
        for node_name, addr in ip_map.items():
            if node_name not in self.IP_map:
                self.IP_map[node_name] = addr

    def search(self, msg, port=MIN_PORT):
        logging.debug(f"Looking on port: {port}")
        if port < MIN_PORT:
            logging.error(f"Searching outside of port range")
            return
        if port > MAX_PORT:
            logging.warning(f"No nodes found on network")
            return
        if len(self.connections) > 0:
            logging.debug(f"Stopping search")
            return
        # if port == self.port:
        #     self.continueSearch(None, msg, port)
        d = self.client(port, announce_msg=msg)
        d.addCallback(self.continueSearch, msg, port)

    def continueSearch(self, prot, msg, port):
        reactor.callLater(0.2, self.search, msg, port + 1)

    def addNodeConnection(self, source, node_name, port=None):
        self.connections[node_name] = source
        peer = source.transport.getPeer()
        if node_name not in self.IP_map:
            logging.debug(f"{node_name} not in IP map, adding...")
            if not port:
                port = peer.port
            addr = f"{peer.host}:{port}"
            self.IP_map[node_name] = addr

    def addNodeAddr(self, node_name, addr):
        if node_name not in self.IP_map:
            logging.debug(f"{node_name} not in IP map, adding...")
            host, port = addr.split(':')
            addr = f"{host}:{port}"
            self.IP_map[node_name] = addr

    def getAddr(self):
        return str(self.addr) + ':' + str(self.port)

    def remove_node_connection(self, node_name):
        p = self.connections.pop(node_name)
        p.disconnect()

    def confirmConnection(self, prot, msg):
        self.sendMsg(msg, None, prot)
        return prot

    def errorHandler(self, e):
        e.trap(ConnectionRefusedError)
