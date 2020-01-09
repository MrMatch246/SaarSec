from __future__ import print_function
import angr
import logging
logging.disable(logging.WARNING)
logging.getLogger().disabled = True

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
        self.proj=angr.Project(config._binaryfile,load_options={"auto_load_libs": False})
        self.stateEn=self.proj.factory.entry_state()
        self.cfg = self.proj.analyses.CFGEmulated(keep_state=True,state_add_options=angr.sim_options.refs,context_sensitivity_level=4)
        self.cdg = self.proj.analyses.CDG(self.cfg)
        self.ddg = self.proj.analyses.DDG(self.cfg)
        #self.getMainState()
        bs = self.getfuncBackSLI("0x004007aa")
        print(bs.dbg_repr(44))

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

    def advanceState(self, adr, sta=None): #
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

    def LogMain(self):

        pass

    def revCons(self):
        pass

    def traceEmu(self,start_addr,end_addr,result,precon):   #precon aka regs of Interest
        print("Tracing from : "+end_addr+" Up to : "+start_addr)
        nextresult = None
        return nextresult