from ICNProtocol import ICNProtocol
from twisted.internet import reactor
from Tlru import TLRU_Table
import ast
import logging
import argparse
from time import time


class Node:

    def __init__(self, node_id=None, port=None, data_n=None, data_v=None):
        self.name = node_id
        self.PIT = TLRU_Table(3)
        self.cache = TLRU_Table(3)
        self.locations = TLRU_Table(3)
        self.peers = []
        self.data = {}

        self.icn = ICNProtocol(self, self.name, port)

        if data_n is not None and data_v is not None:
            self.data[data_n] = (data_v, 60)

    def addToPIT(self, data_name, node_name, ttw, count=1):
        self.PIT.add(data_name, node_name, ttw, count)
        print(self.PIT)

    def removeFromPIT(self, data_name):
        dest, count = self.PIT.remove(data_name)
        return dest, count

    def hasLocation(self, data_name):
        if self.locations.contains(data_name):
            return True
        else:
            return False

    def addLocation(self, data_name, location):
        self.locations.add(data_name, location)

    def getLocation(self, data_name):
        location, t = self.locations.get(data_name)
        return location

    def cacheData(self, data_name, data_val, ttu):
        self.cache.add(data_name, data_val, ttu)

    def addPeer(self, node_name):
        if node_name not in self.peers:
            self.peers.append(node_name)

    def hasData(self, data_name):
        if data_name in self.data:
            return True
        else:
            return False

    def run(self):
        self.reactor = reactor
        self.reactor.run()

    def getData(self, data_name):
        if data_name in self.data:
            data_val, ttu = self.data[data_name]
            ttu += time()
            print(data_val, ttu)
            return data_val, ttu
        else:
            return None

    def requestData(self, data_name, ttw=10):
        ttw += time()
        self.icn.requestData(data_name, ttw)

    def useData(self, data_name, data_val):
        logging.info(f"Received {data_name} with a value of {data_val}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node-name', help='Name for node in this network', type=str)
    parser.add_argument('--port', help='Port for this node', type=int, default=5789)
    parser.add_argument('--data-n', help='Data name for this node', type=str, default=None)
    parser.add_argument('--data-v', help='Data for the node', type=str, default="10")
    parser.add_argument('--logging-level', help='Logging level: 10 - Debug, 20 - Info, 30 - Warnings', type=int, default=10)
    args = parser.parse_args()

    if args.node_name is None:
        print("Please specify a node name")
        exit(1)

    if args.port is None:
        print("Please specify the port for this node")
        exit(1)

    logging.basicConfig(level=args.logging_level)
    logging.debug(f"Running node {args.node_name}")
    n = Node(args.node_name, args.port, args.data_n, args.data_v)
    n.run()


if __name__ == "__main__":
    main()
