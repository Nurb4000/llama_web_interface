Total revamp of the project. Still python, still simplistic but redid the interface to be more friendly, also added RPC options.

Note all bin and models files have been moved to /opt/llama.cpp   but you can always edit it to fit your configuration.
If you go with RPC you will also need RPC llama servers out on your network.  You can read how to do that at llama.cpp but basically you compile with the RPC option, then start the RPC servers on your remote machines.  The IP addresses in this code are for example use only,  you will want to change them to yours of course. 

My local llama server service config also included as its needed to be the 'coordinator' of the process, and what this interface 'updates/restarts' so that it runs on its own after updates.. Even if you don't use their GUI, its needed.


<img width="1880" height="888" alt="image" src="https://github.com/user-attachments/assets/a553be91-edbf-4a42-bd7b-3e758a343c51" />
