# ICN
This is more like an ICN

Mostly working, a few bugs to fix.

After doing more research I think this is more closely aligned to what an ICN should look like. It's true peer to peer, no central nodes, but no big shared tables either. Instead requests should propagate through the network via pending interest tables. I included all the tricks I could find for scalability -we can limit the table sizes and use TLRU to organise them. This means we can cache data along the way, set a time limit for that data (i.e. one minute for one minute interval temperatures updates), and the most frequently accessed data will be prioritised.

In addition to the caching and the natural scalability of the peer to peer design, we can still have small 'location' tables. Basically I set it up so that when data is requested and properly returned to a node, they also receive the address of the node that hosts that data, so in the future they can go directly to them. Again, these tables are limited in size and omtimised using TLRU (or in this case just RLU).

It's a bit late but I think this is the right direction to go. Still have to get it working across multiple pis, so hopefully that's no headache.
