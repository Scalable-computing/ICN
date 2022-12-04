#!/bin/sh
python3 Node.py --node-name Pi1 --port 33011 --data-n dublin &

sleep 8

python3 Node.py --node-name Pi2 --port 33012 --data-n beijing &

python3 Node.py --node-name Pi3 --port 33013 --data-n capetown &

python3 Node.py --node-name Pi4 --port 33014 --data-n doha &

python3 UserNode.py --node-name Pi5 --port 33015 --data-n amsterdam
