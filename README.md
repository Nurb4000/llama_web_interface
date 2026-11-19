Total revamp of the project. Still python, still simplistic but redid the interface to be more friendly and embedded into one file. Also added RPC options. Added a few more command parameters as well. This includes mmproj for multi-modal and some 'space saver' cache options. Also tossed in the vulcan option. 

Note all bin and models files have been moved to /opt/llama.cpp   but you can always edit it to fit your configuration.
If you go with RPC you will also need RPC llama servers out on your network.  You can read how to do that at llama.cpp but basically you compile with the RPC option, then start the RPC servers on your remote machines.  The IP addresses in this code are for example use only,  you will want to change them to yours of course. 

My local llama server service config also included as its needed to be the 'coordinator' of the process, and what this interface 'updates/restarts' so that it runs on its own after updates.. Even if you don't use their GUI, its needed.

Current state:

<img width="1902" height="930" alt="image" src="https://github.com/user-attachments/assets/4ede77d4-07c3-40b3-862d-61ce065ad1ee" />

