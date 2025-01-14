from __future__ import print_function
import logging
import angr
logging.root.handlers.clear()
from pwn import *
import claripy
global config

def i2hs(zahl):
    return str(hex(zahl))
def hs2i(hexstr):
    return int(hexstr, 16)


class LogicANGR:

    def __init__(self,confi):

        self.logGen = log.progress("Stage 2", level=31)
        self.logGen.status("Loading Binary Into Angr")

        global config
        config = confi
        self.proj=angr.Project(config._binaryfile,load_options={"auto_load_libs": False})

        self.logGen.status("Finished Loading! Mapping Graphs now!")

        self.stateEn=self.proj.factory.entry_state()

        self.cfg = self.proj.analyses.CFGEmulated(keep_state=True,state_add_options=angr.sim_options.refs,context_sensitivity_level=4)
        self.cdg = self.proj.analyses.CDG(self.cfg)
        self.ddg = self.proj.analyses.DDG(self.cfg)

        self.logGen.status("Graphs Mapped! Trying to find exploitable Path now! This may take a while!")

        self.marker=b'i'*(self.stateEn.arch.bits // 8)
        self.expStates = self.expStateFindr()
        self.iteration=0
        self.iterationS=len(self.expStates)
        self.nextIteration()
        self.logGen.success("Vulnerability found and Mysteries solved!")

        #bs = self.getfuncBackSLI("0x004007aa")
        #print(bs.dbg_repr(44))


    def nextIteration(self):
        if self.iteration < self.iterationS:
            self.statalizer(self.expStates[self.iteration])
            self.iteration+=1
            return True
        else:
            return False

    def statalizer(self,state):
        stdinlist=state.posix.stdin.concretize()
        stdoutlist=state.posix.stdout.concretize()
        prelist=list()
        vulnlist = list()
        postlist = list()
        outlist = list()
        found=False
        for input in stdinlist:
            if self.marker not in input and not found:
                prelist.append(input[:-1])
            elif self.marker not in input and found:
                postlist.append(input)
            elif self.marker in input:
                vulnlist.append(input)
            else:
                print("something Broke @ statalizer ")
                exit(0)
        if not vulnlist:
            print("couldnt find Vuln Input @ statalizer")
            exit(0)
        vuln=vulnlist[0]
        vulnparts=vuln.split(self.marker)
        for output in stdoutlist:
            if len(output)>1:
                outlist.append(output)

        config._output=outlist
        config._input=prelist
        config._payroll = len(vulnparts[0])
        config._payloadsize= len(self.marker)+len(vulnparts[1])
        config._bufferA=config._payroll*"A"


    def expStateFindr(self): #seems pretty DONE :D
        p = angr.Project(config._binaryfile)
        extras = {angr.sim_options.REVERSE_MEMORY_NAME_MAP, angr.sim_options.TRACK_ACTION_HISTORY}
        es = p.factory.entry_state(add_options=extras)
        sm = p.factory.simulation_manager(es, save_unconstrained=True)
        exploitable_state = []
        while len(sm.active) > 0:
            sm.step()
            if len(sm.unconstrained) > 0:
                for state in sm.unconstrained:
                    eip = state.regs.pc
                    bits = state.arch.bits
                    state_copy = state.copy()
                    constraints = []
                    for i in range(bits // 8):
                        curr_byte = eip.get_byte(i)
                        constraint = claripy.And(curr_byte == 0x69)
                        constraints.append(constraint)
                    if state_copy.solver.satisfiable(extra_constraints=constraints):
                        for constraint in constraints:
                            state_copy.add_constraints(constraint)
                        exploitable_state.append(state_copy)
                sm.drop(stash='unconstrained')
        eplist = []
        for ep in exploitable_state:
            try:
                assert ep.solver.symbolic(ep.regs.pc), "PC must be symbolic at this point"
                eplist.append(ep)
            except:
                pass
        if eplist == []:
            print("no exploitable state has been found @ expStateFindr ")
            exit(0)
        else:
            return eplist

    def fully_symbolic(self, state, variable):
        for i in range(state.arch.bits):
            if not state.solver.symbolic(variable[i]):
                return False

        return True

    def check_continuity(self,address, addresses, length):
        for i in range(length):
            if not address + i in addresses:
                return False
        return True

    def find_symbolic_buffer(self,state, length):
        stdin = state.posix.stdin
        sym_addrs = []
        for _, symbol in state.solver.get_variables('file', stdin.ident):
            sym_addrs.extend(state.memory.addrs_for_name(next(iter(symbol.variables))))

        for addr in sym_addrs:
            if self.check_continuity(addr, sym_addrs, length):
                yield addr

    def getfuncBackSLI(self,target):
        global tar_nod
        if type(target) is str:
            try:
                tar = hs2i(target)
                tar_nod = self.cfg.get_any_node(tar)
            except:
                try:
                    tar_fun = self.cfg.kb.functions.function(name=target)
                    tar_nod = self.cfg.get_any_node(tar_fun.addr)
                except:
                    print("function : "+ target + " IS NOT found! Use an address as Argument!  <called by getfuncBackSLI>")
                    exit(0)
        else:
            tar_nod = self.cfg.get_any_node(target)
        return self.proj.analyses.BackwardSlice(self.cfg, cdg=self.cdg, ddg=self.ddg, targets=[(tar_nod, -1)])

    def getMainState(self):
        return self.advanceState(config._main)



    def advanceState(self, adr, sta=None):
        if type(adr) is int:
            addr=adr
        else:
            addr=hs2i(adr)
        if sta:
            state=sta
        else:
            state=self.stateEn
        simman=self.proj.factory.simulation_manager(state)
        stepper = (simman.active[0]).addr
        while (stepper != addr):
            simman.step()
            stepper = (simman.active[0]).addr
            #print(simman.active)
        return simman.active[0]

    def getFuncAddress(self,funcName, plt=None):
        found = [
            addr for addr, func in self.cfg.kb.functions.items()
            if funcName == func.name and (plt is None or func.is_plt == plt)
        ]
        if len(found) > 0:
            print("Found " + funcName + "'s address at " + hex(found[0]) + "!")
            return found[0]
        else:
            raise Exception("No address found for function : " + funcName)

    def revCons(self):
        pass

    def traceEmu(self,start_addr,end_addr,result,precon):   #precon aka regs of Interest
        print("Tracing from : "+end_addr+" Up to : "+start_addr)
        nextresult = None
        return nextresult