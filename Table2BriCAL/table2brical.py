#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
table2brical.py
=====

This module contains the class `Table2BriCAL` which converts table files
describing connectome into a BriCA language JSON file.


"""

import sys
import os
import json

class Table2BriCAL:
    """
    converts table files describing connectome into a BriCA language JSON file.
    """

    def __init__(self):
        self.json={}
        self.connection={}
        self.regions={}
        self.superModules={}
        self.subModules={}
        self.modules={}
        self.ports=[]
        self.connections=[]
        self.headItems=None

    def loadConnection(self, path):
        heading = True
        for line in open(path, 'r'):
            items = line[:-1].split('\t')
            if heading:
                self.headItems = items[1:]
                heading = False
            else:
                self.connection[items[0]]=items[1:]

    def loadRegions(self, path):
        for line in open(path, 'r'):
            items = line[:-1].split('\t')
            if len(items) < 4:
                break
            module={}
            module["Name"]=items[1]
            module["Comment"]=items[3]
            self.modules[items[0]]=module

    def loadHierarchy(self, path):
        for line in open(path, 'r'):
            items = line[:-1].split('\t')
            if items[0] in self.modules and items[1] in self.modules:
                self.superModules[items[0]] = items[1]
                if items[1] in self.subModules:
                    subModules = self.subModules[items[1]]
                else:
                    subModules = []
                subModules.append(items[0])
                self.subModules[items[1]] = subModules

    def build(self, threshold):
        for id in self.connection:
            originName = self.modules[id]["Name"]
            items = self.connection[id]
            for i in range(0, len(items)):
                try:
                    if items[i].strip() == '':
                        items[i] = '0'
                    var = float(items[i])
                except:
                    print "Cannot convert item " + str(i) + ":'" + items[i] + "' for id:" + id + "."
                    print items
                if var >= threshold:
                    targetID = self.headItems[i]
                    targetName = self.modules[targetID]["Name"]
                    originModule = self.modules[id]
                    self.createPort("Output", originModule, originName, targetName)
                    targetModule = self.modules[targetID]
                    self.createPort("Input", targetModule, originName, targetName)
                    self.createConnection(id, targetID)
        self.addHierarchyToModules()

    def createPort(self, type, module, origin, target):
        portName = origin + "-" + target + "-" + type
        if "Ports" in module:
            ports = module["Ports"]
        else:
            ports = []
        ports.append(portName)
        module["Ports"] = ports
        port = {}
        port["Name"] = portName
        port["Module"] = module["Name"]
        port["Type"] = type
        port["Shape"] = [ 10 ]
        if type == "Input":
            port["Comment"] = "An input port of " + target + " for connection from " + origin
        else:
            port["Comment"] = "An output port of " + origin + " for connection to " + target
        self.ports.append(port)

    def createConnection(self, originID, targetID):
        originName = self.modules[originID]["Name"]
        targetName = self.modules[targetID]["Name"]
        connection = {}
        connectionName = originName + "-" + targetName
        connection["Name"] = connectionName
        connection["FromModule"] = originName
        connection["ToModule"] = targetName
        outputPortName = originName + "-" + targetName + "-Output"
        inputPortName = originName + "-" + targetName + "-Input"
        connection["FromPort"] = outputPortName # self.getPath(originID) + "/" + outputPortName
        connection["ToPort"] = inputPortName    # self.getPath(targetID) + "/" + inputPortName
        connection["Comment"] = "A connection from " + originName + " to " + targetName
        self.connections.append(connection)

    def addHierarchyToModules(self):
        for moduleID in self.modules:
            module = self.modules[moduleID]
            if moduleID in self.superModules:
                module["SuperModule"] = self.superModules[moduleID]
            if moduleID in self.subModules:
                module["SubModules"] = self.subModules[moduleID]

    def getPath(self, id):
        pathList = [id]
        while id in self.superModules:
            pathList.append(self.superModules[id])
            id = self.superModules[id]
        path = ""
        for id in reversed(pathList):
            if path == "":
                path = self.modules[id]["Name"]
            else:
                path = path + "/" + self.modules[id]["Name"]
        return path

    def writeJSON(self, path, base):
        fp = open(path, 'w')
        header = {}
        header["Type"]="A"
        basename = os.path.basename(path)
        if "." in basename:
            header["Name"]=basename[0:basename.rfind(".")]
        else:
            header["Name"] = basename
        header["Base"] = base
        self.json["Header"]=header
        modules = []
        for module in self.modules:
            modules.append(self.modules[module])
        self.json["Modules"]=modules
        self.json["Ports"] = self.ports
        self.json["Connections"] = self.connections
        json.dump(self.json, fp, indent=1)
        fp.close()

if __name__ == "__main__":
    if len(sys.argv)!=7:
        print "Usage: table2brical.py connection.txt regions.txt hierarchy.txt output.json prefix threshold"
        quit()
    params = sys.argv
    threshold = float(params[6])
    t2b = Table2BriCAL()
    t2b.loadConnection(params[1])
    t2b.loadRegions(params[2])
    t2b.loadHierarchy(params[3])
    t2b.build(threshold)
    t2b.writeJSON(params[4], params[5])
