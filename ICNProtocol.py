from IPNode import IPNode
import logging
import json

ANNOUNCE = 'ANNOUNCE'
ACKNOWLEDGE = 'ACKNOWLEDGE'
REQUEST = 'REQUEST'
FAIL = 'FAIL'
DATA = 'DATA'

DN = 'data_name'
DV = 'data_val'
TTU = 'time_to_use'
LOC = 'location'
TTW = 'time_to_wait'


# Represents ICN protocol
class ICNProtocol:
    def __init__(self, node, node_id, port):
        self.node = node
        self.ip_node = IPNode(self, node_id, port)
        self.ip_node.search(self.sendMsg(ANNOUNCE, None))

    def newConnection(self, source=None):
        self.sendMsg(ANNOUNCE, None)

    # Sends a message with format {id:__, msg_type:__, content:__, ttl:__} where id is the sender's
    # name, msg_type is the message type and content could be a piece of data, a location (node name)
    # for some data, etc. TTL is time to live, i.e. how many hops for a request.
    def sendMsg(self, msg_type, node_name, content="", ttl=1):
        print(self.node.PIT.vals)
        msg = json.dumps({'id': self.node.name, 'type': msg_type, 'content': content, 'ttl': ttl})
        logging.info(f"[Sending message: {msg_type} to {node_name}] ")
        logging.debug(f"Message: {msg}")
        if node_name is not None:
            self.ip_node.sendMsg(msg, node_name)
        return msg

    # Handles a given message. Decides what to do based on the msg_type.
    def handleMsg(self, msg, source=None):
        msg = json.loads(msg)
        msg_type, node_name, content, ttl = msg['type'], msg['id'], msg['content'], msg['ttl']

        if msg_type == ANNOUNCE:
            self.handleAnnounce(node_name, source)

        elif msg_type == ACKNOWLEDGE:
            self.handleAcknowledge(node_name, source)
            return True

        elif msg_type == REQUEST:
            c = json.loads(content)
            logging.info(f"[Location request received from {node_name} for {c[DN]}, {ttl}]")
            self.handleRequest(node_name, c[DN], c[TTW], ttl)

        elif msg_type == FAIL:
            c = json.loads(content)
            logging.info(f"[Fail from {node_name} for {c[DN]}]")
            self.handleFail(node_name, c[DN])

        elif msg_type == DATA:
            c = json.loads(content)
            logging.info(f"[Data received from {node_name} for {c[DN]} : {c[DV]}]")
            self.handleData(node_name, c[DN], c[DV], c[TTU], c[LOC])

    def handleAnnounce(self, node_name, source):
        print(node_name)
        if node_name == self.node.name:
            logging.info(f"Connection to self - {node_name} to {self.node.name}; disconnecting...")
            source.disconnect()
            return
        logging.info(f"[Announcement received from {node_name}]")
        self.ip_node.addNodeConnection(source, node_name)
        self.node.addPeer(node_name)
        self.sendMsg(ACKNOWLEDGE, node_name)

    def handleAcknowledge(self, node_name, source):
        logging.info(f"[Acknowledgement received from {node_name}]")
        self.ip_node.addNodeConnection(source, node_name)
        self.node.addPeer(node_name)

    def handleRequest(self, node_name, data_name, ttw, ttl):
        if self.node.hasData(data_name):
            # Has data -> reply with data
            data_val, ttu = self.node.getData(data_name)
            content = json.dumps({DN: data_name, DV: data_val, TTU: ttu, LOC: self.ip_node.getAddr()})
            self.sendMsg(DATA, node_name, content)
            return

        elif ttl == 1:
            # Reply with fail
            content = json.dumps({DN: data_name})
            self.sendMsg(FAIL, node_name, content)

        else:
            # Propagate request
            self.node.addToPIT(data_name, node_name, ttw)
            content = json.dumps({DN: data_name, TTW: ttw})
            if self.node.hasLocation(data_name):
                # Send to guaranteed node
                self.sendMsg(REQUEST, self.getLoc(data_name), content)
            else:
                # Send to all other peers
                count = 1
                for n in self.node.peers:
                    if n == node_name:
                        continue
                    self.node.addToPIT(data_name, node_name, count)
                    count += 1
                    self.sendMsg(REQUEST, n, content)

    def handleFail(self, node_name, data_name):
        logging.info(f"[Fail from {node_name} for {data_name}]")
        # NODE PIT TABLE -1 REMAINING
        dest, r = self.node.removeFromPIT(data_name)
        # IF remaining = 0 send fail
        if r == 0 and dest != self.node.name:
            content = json.dumps({DN: data_name})
            self.sendMsg(FAIL, dest, content)
        elif dest == self.node.name:
            logging.warning(f"Data for {data_name} could not be found on network")

    def handleData(self, node_name, data_name, data_val, ttu, location):
        # NODE REMOVE PIT -> CHECK
        dest, r = self.node.removeFromPIT(data_name)
        if dest == self.node.name:
            self.node.addLocation(data_name, node_name)
            self.ip_node.addNodeAddr(node_name, location)
            self.node.useData(data_name, data_val)
        else:
            content = json.dumps({DN: data_name, DV: data_val, TTU: ttu, LOC: location})
            self.sendMsg(DATA, dest, content)
            self.node.cacheData(data_name, data_val, ttu)

    def requestData(self, data_name, ttw, ttl=3):
        self.node.addToPIT(data_name, self.node.name, ttw)
        if self.node.hasData(data_name):
            data_val, ttu = self.node.getData(data_name)
            self.handleData(self.node.name, data_name, data_val, ttu, self.node.name)
        elif self.node.hasLocation(data_name):
            content = json.dumps({DN: data_name, TTW: ttw})
            self.sendMsg(REQUEST, self.node.getLocation(data_name), content, ttl)
        else:
            content = json.dumps({DN: data_name, TTW: ttw})
            count = 1
            for n in self.node.peers:
                if n == self.node.name:
                    continue
                self.node.addToPIT(data_name, self.node.name, ttw, count)
                count += 1
                self.sendMsg(REQUEST, n, content, ttl)