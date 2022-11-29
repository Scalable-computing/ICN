from IPNode import IPNode, LOCAL
import logging
import json
from cryptography.fernet import Fernet


HANDSHAKE_TIME_LIMIT = 10
NO_ADDR = 'NO_ADDRESS'

# Message types
ANNOUNCE = 'ANNOUNCE'
ACKNOWLEDGE = 'ACKNOWLEDGE'
REQUEST = 'REQUEST'
DIR_REQUEST = 'DIRECT_REQUEST'
FAIL = 'FAIL'
DATA = 'DATA'

# Content values
DN = 'data_name'
DV = 'data_val'
TTU = 'time_to_use'
LOC = 'location'
LOCN = 'location_name'
TTW = 'time_to_wait'
PRT = 'port'


# Represents ICN protocol
class ICNProtocol:
    def __init__(self, node, node_id, port):
        self.node = node
        self.ip_node = IPNode(self, node_id, port)
        self.ip_node.search(self.sendMsg(ANNOUNCE, None, json.dumps({PRT: self.ip_node.getPort()}), 2))

    # Sends a message with format {id:__, msg_type:__, content:__, ttl:__} where id is the sender's
    # name, msg_type is the message type and content could be a piece of data, a location (node name)
    # for some data, etc. TTL is time to live, i.e. how many hops for a request.
    def sendMsg(self, msg_type, node_name, content="", ttl=1):
        msg = json.dumps({'id': self.node.name, 'type': msg_type, 'content': content, 'ttl': ttl})
        logging.info(f"[Sending message: {msg_type} to {node_name}] ")
        logging.debug(f"Message: {msg}")
        if node_name is not None:
            self.ip_node.sendMsg(msg, node_name)
        return msg

    # Handles a given message. Decides what to do based on the msg_type.
    def handleMsg(self, msg, source=None):
        logging.debug(msg)
        msg = json.loads(msg)
        msg_type, node_name, content, ttl = msg['type'], msg['id'], msg['content'], msg['ttl']
        c = json.loads(content)

        if msg_type == ANNOUNCE:
            self.handleAnnounce(node_name, c[PRT], source, ttl)

        elif msg_type == ACKNOWLEDGE:
            self.handleAcknowledge(node_name, c[PRT], source, ttl)

        elif msg_type == REQUEST:
            logging.info(f"[Request received from {node_name} for {c[DN]}, {ttl}]")
            self.handleRequest(node_name, c[DN], c[TTW], ttl)

        elif msg_type == FAIL:
            self.handleFail(node_name, c[DN])

        elif msg_type == DATA:
            logging.info(f"[Data received from {node_name} for {c[DN]} : {c[DV]}]")
            self.handleData(node_name, c[DN], c[DV], c[TTU], c[LOC])

        elif msg_type == DIR_REQUEST:
            self.handleDirectRequest(node_name, c[DN], c[TTW], c[PRT], source)

    def handleAnnounce(self, node_name, port, source, ttl):
        if node_name == self.node.name:
            logging.info(f"Connection to self - {node_name} to {self.node.name}; disconnecting...")
            source.disconnect()
            return

        self.ip_node.isolated = False
        if not self.ip_node.part_of_network:
            source.disconnect()
            return

        logging.info(f"[Announcement received from {node_name}]")
        self.ip_node.addNodeAddr(node_name, port, None, source)
        self.node.reactor.callLater(HANDSHAKE_TIME_LIMIT, self.ip_node.verifyPeer, node_name)
        content = json.dumps({PRT: self.ip_node.getPort()})
        self.sendMsg(ACKNOWLEDGE, node_name, content, ttl)

    def handleAcknowledge(self, node_name, port, source, ttl):
        logging.info(f"[Acknowledgement received from {node_name}]")
        self.ip_node.addNodeAddr(node_name, port, None, source)
        self.ip_node.addNodeConnection(node_name, source)
        self.node.addPeer(node_name)
        if ttl > 1:
            ttl -= 1
            content = json.dumps({PRT: self.ip_node.getPort()})
            self.sendMsg(ACKNOWLEDGE, node_name, content, ttl)
    def encrypt_data_val(self,data_val):
        print("*****************Encryption***********")
        key = b'5sb7hUkLx4O9eN0eyFT0rVl1TEXJ6C2Gm1FjGFydCBA='
        f = Fernet(key)
        token = f.encrypt(bytes(str(data_val),'UTF-8'))
        return token.decode("utf-8")

    def handleRequest(self, node_name, data_name, ttw, ttl):
        ttl -= 1
        # Has data -> reply with data
        if self.node.hasData(data_name):
            data_val, ttu = self.node.getData(data_name)
            print(data_val)
            data_val=self.encrypt_data_val(data_val)
            
            content = json.dumps({DN: data_name, DV: data_val, TTU: ttu, LOC: NO_ADDR})
            self.sendMsg(DATA, node_name, content)
            return
        elif self.node.hasCache(data_name):
            data_val, ttu = self.node.getCache(data_name)
            content = json.dumps({DN: data_name, DV: data_val, TTU: ttu, LOC: NO_ADDR})
            self.sendMsg(DATA, node_name, content)
            return
        # Time to live has run out -> reply with fail
        elif ttl == 0:
            content = json.dumps({DN: data_name})
            self.sendMsg(FAIL, node_name, content)
        # Data name already in PIT -> do nothing
        elif self.node.hasPITEntry(data_name):
            return
        else:
            # Propagate request
            self.node.addToPIT(data_name, node_name, ttw)
            content = json.dumps({DN: data_name, TTW: ttw})
            if self.node.hasLocation(data_name):
                # Send to guaranteed node
                self.sendMsg(REQUEST, self.getLocation(data_name), content, ttl)
            else:
                # Send to all other peers
                count = 1
                for n in self.node.peers:
                    if n == node_name:
                        continue
                    self.node.addToPIT(data_name, node_name, ttw, count)
                    count += 1
                    self.sendMsg(REQUEST, n, content, ttl)
                if count == 1:
                    self.sendMsg(FAIL, node_name, content)

    def handleFail(self, node_name, data_name):
        # Remove count of item from PIT
        dest, r = self.node.removeCountFromPIT(data_name)
        # Data not in PIT -> do nothing
        if dest is None:
            return
        logging.info(f"[Fail from {node_name} for {data_name}]")
        # If final count of item has been removed from PIT -> forward FAIL to destination
        if r == 0 and dest != self.node.name:
            content = json.dumps({DN: data_name})
            self.sendMsg(FAIL, dest, content)
        # If final count of item has been removed AND this node is the destination -> Data not found
        elif r == 0 and dest == self.node.name:
            logging.warning(f"Data for {data_name} could not be found on network")
    def decrypt_data_val(self,data_val):
        print("*****************Decryption***********")
        key = b'5sb7hUkLx4O9eN0eyFT0rVl1TEXJ6C2Gm1FjGFydCBA='
        f = Fernet(key)
        token = f.decrypt(bytes(data_val,'UTF-8'))
        return  token.decode("utf-8")      

    def handleData(self, node_name, data_name, data_val, ttu, location):
        dest, r = self.node.removeFromPIT(data_name)
        # Data not in PIT -> do nothing
        if dest is None:
            return
        # Data in PIT, requested by this node -> update location for data & use data
        if dest == self.node.name:
            location = self.updateMessageLocation(node_name, location)
            self.addLocation(data_name, location)
            data_val = self.decrypt_data_val(data_val)
            self.node.useData(data_name, data_val)
        # Data in PIT, requested by other node -> forward data + cache data
        else:
            location = self.updateMessageLocation(node_name, location)
            content = json.dumps({DN: data_name, DV: data_val, TTU: ttu, LOC: location})
            self.sendMsg(DATA, dest, content)
            self.node.cacheData(data_name, data_val, ttu)
        if node_name not in self.node.peers:
            self.ip_node.removePeer(node_name)

    def handleDirectRequest(self, node_name, data_name, ttw, port, source):
        logging.info(f"[Direct Request received from {node_name}]")
        self.ip_node.addNodeAddr(node_name, port, None, source)
        content = json.dumps({PRT: self.ip_node.getPort()})

        if self.node.hasData(data_name):
            data_val, ttu = self.node.getData(data_name)
            data_val=self.encrypt_data_val(data_val)
            print(data_val)
            content = json.dumps({DN: data_name, DV: data_val, TTU: ttu, LOC: None})
            self.sendMsg(DATA, node_name, content)
        else:
            content = json.dumps({DN: data_name})
            self.sendMsg(FAIL, node_name, content)
        if node_name not in self.node.peers:
            self.node.reactor.callLater(HANDSHAKE_TIME_LIMIT, self.ip_node.removePeer, node_name)

    def addLocation(self, data_name, location):
        if location is not None and location != NO_ADDR:
            host, port, node_name = location.split(':')
            self.node.addLocation(data_name, node_name)
            self.ip_node.addNodeAddr(node_name, port, host)

    # Update the location of data
    def updateMessageLocation(self, node_name, location):
        if location is None:
            return None
        addr = self.ip_node.getPeerAddr(node_name)
        if addr is None:
            return None
        if location == NO_ADDR:
            return f"{addr}:{node_name}"
        try:
            host, port, name = location.split(':')
        except Exception:
            logging.debug(f"Could not decode {location}")
            return None
        host = addr.split(':')[0]
        if host not in LOCAL:
            return f"{host}:{port}:{node_name}"
        return location

    def requestData(self, data_name, ttw, ttl=5):
        # Add data to PIT
        self.node.addToPIT(data_name, self.node.name, ttw)
        # If this node contains data, handle it
        if self.node.hasData(data_name):
            data_val, ttu = self.node.getData(data_name)
            self.handleData(self.node.name, data_name, data_val, ttu, self.ip_node.getPeerAddr(self.node.name))
        # If this node knows location of data, request directly
        elif self.node.hasLocation(data_name):
            node_name = self.node.getLocation(data_name)
            if node_name in self.node.peers:
                content = json.dumps({DN: data_name, TTW: ttw})
                self.sendMsg(REQUEST, node_name, content, 1)
            else:
                content = json.dumps({DN: data_name, TTW: ttw, PRT: self.ip_node.getPort()})
                self.sendMsg(DIR_REQUEST, self.node.getLocation(data_name), content, ttl)
        # If this node has no peers, search for peers
        elif len(self.node.peers) < 1:
            logging.warning(f"{self.node.name} has no peers for data request.")
            self.handleFail(FAIL, self.node.name, data_name)
            # Search
            self.ip_node.search()
        # Otherwise send requests to all peers
        else:
            content = json.dumps({DN: data_name, TTW: ttw})
            count = 1
            for n in self.node.peers:
                if n == self.node.name:
                    continue
                self.node.addToPIT(data_name, self.node.name, ttw, count)
                count += 1
                self.sendMsg(REQUEST, n, content, ttl)
