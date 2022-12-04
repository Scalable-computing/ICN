# ICN

IMPORTANT: Please ensure that whenever running any code that there are no processes running on a certain port. For our code an easy way to fix this is:
pkill -f Node.py
This will stop all background node processes. The shell script will create some of these processes in the terminal, so please be aware.
This functionality is intended as every node is its own independent process which better represents a peer to peer network.



Please run the shell script included: runme.sh

bash runme.sh

This will set up the network. There will be a delay between the first node and the rest. Once the other nodes pop up and you see various acknowledgement messages, you can dontinue. You are controlling one of the nodes (amsterdam). Now you can enter data names to request them. Try these:
dublin_temp
beijing_snow
capetown_per

Enter dublin_temp again, and you should see that it directly requests data. (it may still appear as a normal request message if node is already a peer, but there will only be one. If not the data may have expired, try again but faster)

The cities here are dublin, beijing, capetown, doha and amsterdam. The data types are temp, hum, wind, water, per, bar, snow, cloud.
A data name is a combination of these: capetown_temp, doha_wind, etc. Feel free to enter different data names.

If for some reason this does not work, more detailed instructions are included in a pdf. 

Again please ensure to run 'pkill -f Node.py' to kill the background processes associated with this script, after you have quit or ended the user node process.

Finally some data generation diagrams are included in the associated folder.