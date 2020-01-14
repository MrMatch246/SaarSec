from __future__ import print_function
import angr
import logging
#logging.disable(logging.WARNING)
#logging.getLogger().disabled = True
logging.getLogger("angr").setLevel("CRITICAL")
global config

def i2hs(zahl):
    return str(hex(zahl))
def hs2i(hexstr):
    return int(hexstr, 16)


class LogicANGR:

    def __init__(self,confi):
        global config
        config = confi
        #print(i2hs(config._main))
        self.proj=angr.Project(config._binaryfile,load_options={"auto_load_libs": True})
        self.stateEn=self.proj.factory.entry_state()
        self.cfg = self.proj.analyses.CFGEmulated(keep_state=True,state_add_options=angr.sim_options.refs,context_sensitivity_level=4)
        self.cdg = self.proj.analyses.CDG(self.cfg)
        self.ddg = self.proj.analyses.DDG(self.cfg)
        #self.reglist=["rdi","rdx","rsi","rdi","rdi","rdi",]
        #main_state = self.getMainState()
        #bs = self.getfuncBackSLI("0x004007aa")
        #print(bs.dbg_repr(44))
        es = self.expStateFindr()
        for x in range(10):
            try:
                print(es.posix.dumps(x))
            except:
                break

    def LogMain(self):

        pass
    def expStateFindr(self):
        p = angr.Project(config._binaryfile)
        extras = {angr.sim_options.REVERSE_MEMORY_NAME_MAP, angr.sim_options.TRACK_ACTION_HISTORY}
        es = p.factory.entry_state(add_options=extras)
        sm = p.factory.simulation_manager(es, save_unconstrained=True)
        exploitable_state = None
        while exploitable_state is None and len(sm.active) > 0:
            print(sm)
            sm.step()
            if len(sm.unconstrained) > 0:
                for u in sm.unconstrained:
                    if self.fully_symbolic(u, u.regs.pc):
                        exploitable_state = u
                        break

                # no exploitable state found, drop them
                sm.drop(stash='unconstrained')
        ep = exploitable_state
        try:
            assert ep.solver.symbolic(ep.regs.pc), "PC must be symbolic at this point"
        except:
            print("no exploitable state has been found @ expStateFindr ")
            exit()
        return ep

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