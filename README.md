# AutoBufferExploit
Home for Automation Tools and Stuff

Usage: $python3 AutoBufferExploit.py -f <binaryname> -vic <ip> <port> 
This tool uses angr to find magic input string
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
```
-f <filename> 
-core                   #(Use coredumps)
-vic <ip> <port>        #(remote IP and Port)
-ibu <startbufsize>
-das                    #(Pwntools dealarm shell)
-loc                    #(localonly)
-fupa <fullPath>
-h                      #(help)
-gen <generator>        #(ropper(default)/RopGad/ropperService/RopGen)
-debug                  #(noCore)
-debugCore              #(debug with coredump,only local)
-a <attackType>         #(rop(default)/ret2libc/SOS(shellcode on stack(WIP!!))
-libc <path to libc>
-flag                   #(auto cat flag*)
-cmd  <shellcommand>    #(custom shell command to be executed as string)
-dev                    #Enables Dev stuff
-init                   #(WIP! Sets Up ToolChain Run once)
```
