# AutoBufferExploit
Home for Automation Tools and Stuff

```
This tool uses angr to find magic input string
If this is not working you can insert this in the midroll function and consider checking the postroll function which catches unwanted stuff that comes back.
It is capable of:
  -automatically leaking remote libcs
  -generating payloads and sending them
  -do this on static but non-stripped binarys 
  -do this locally
  -and some WIP stuff
It is NOT capable of:
  -solving your Homework
  -pwning random canaries
  -flying
  -bringing you Coffee while you wait for your Flag (WiP?)
THIS TOOL IS WIP!!!

  
Usage: $python3 AutoBufferExploit.py -f <binaryname> -vic <ip> <port>   
-f <filename> 
-core                   #(Use coredumps)
-vic <ip> <port>
-ibu <startbufsize>
-NoDas                  #(No dealarm shell)
-loc                    #(localonly)
-fupa <fullPath>
-h                      #(help)
-gen <generator>        #(ropper(default)/RopGad/ropperService/RopGen)
-debug                  #(noCore)
-debugCore              #(debug with coredump,only local)
-a <attackType>         #(rop(default)/ret2libc/SOS(shellcode on stack(WIP!!))
-libc <path to libc>
-flag                   #(auto cat flag.txt;cat flag)
-cmd  <shellcommand>   #(custom shell command to be executed as string)
-man (use for manual midroll and postroll)
-dev                    #Enables Dev stuff
-init                   #(WIP! Sets Up ToolChain Run once)
```
