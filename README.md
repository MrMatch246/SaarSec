# AutoBufferExploit
Home for Automation Tools and Stuff

Usage: to Work correctly you have to fill out the midroll and postroll(when using ret2libc etc..)
 to ensure that the script gets the correct vulnerable entrypoint!(or try the -dev :D maybe your lucky)

```python
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
