# Dara
from Node import Node
from twisted.internet import reactor
from threading import Thread
import logging
import argparse
import time


class UserNode(Node):

    def readInput(self):
        inp = input("Data name or quit: \n")
        if inp == "quit":
            return False
        if inp == "state":
            print(self)
        else:
            self.reactor.callFromThread(self.requestData, inp, 20)
        time.sleep(1)
        return True

    def run(self):
        self.reactor = reactor
        self.reactor.run(installSignalHandlers=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node-name', help='Name for node in this network', type=str)
    parser.add_argument('--port', help='Port for this node', type=int, default=5789)
    parser.add_argument('--data-n', help='Data name for this node', type=str, default=None)
    parser.add_argument('--data-v', help='Data for the node', type=str, default="10")
    parser.add_argument('--logging-level', help='Logging level: 10 - Debug, 20 - Info, 30 - Warnings', type=int, default=20)
    args = parser.parse_args()

    if args.node_name is None:
        print("Please specify a node name")
        exit(1)

    if args.port is None:
        print("Please specify the port for this node")
        exit(1)

    logging.basicConfig(level=args.logging_level, format='{0:8}%(levelname)-8s %(message)s'.format(args.node_name + ':'))
    n = UserNode(args.node_name, args.port, args.data_n, args.data_v)
    th = Thread(target=n.run, daemon=True)
    th.start()
    receive_input = True
    while receive_input:
        receive_input = n.readInput()


if __name__ == "__main__":
    main()
