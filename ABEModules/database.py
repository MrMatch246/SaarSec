import json


class Database:
    def __init__(self):
        self.db=None
        self.startup()
        self.targets=self.db['targets']
        print(self.db)



    def addTarget(self,name,ip,port,addict=None):
        if not addict:
            self.targets[name]={'ip':ip,'port':port}
        elif type(addict)==dict:
            tmp={'ip':ip,'port':port}
            for key in addict:
                tmp[key]=addict[key]
            self.targets[name]=tmp

    def remTarget(self,name):
        del self.targets[name]

    def getTarget(self,name,all=False):
        if all:
            return self.targets[name]
        else:
            return self.targets[name]['ip'], self.targets[name]['port']

    def update(self):
        self.shutdown()
        self.startup()

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        with open("./ABEModules/db/db.json","w") as database:
            json.dump(self.db,database)

    def startup(self):
        with open("./ABEModules/db/db.json") as database:
            self.db=json.load(database)
