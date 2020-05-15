import os

class StaticHydra:
    def __init__(self,confi):
        global config
        config=confi
        self.path="./ABEToolChain/ghidra/"
        self.pathead=self.path+"support/"
        self.pathANA=self.pathead+"analyzeHeadless "
        self.createProject()

    def createProject(self):
        globals()
        if not os.path.isdir("./ABEToolChain/HydraProject"):
            os.mkdir("./ABEToolChain/HydraProject")
        cmd = self.pathANA+os.getcwd()+"/ABEToolChain HydraProject -import "+config._elf.path
        os.system(cmd)
