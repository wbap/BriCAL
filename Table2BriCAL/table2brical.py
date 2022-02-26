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
        self.json = {}
        self.connection = {}
        self.regions = {}
        self.superModules = {}
        self.subModules = {}
        self.modules = {}
        self.ports = []
        self.connections = []
        self.headItems = None

    def load_connection(self, path):
        heading = True
        for line in open(path, 'r'):
            items = line[:-1].split('\t')
            if heading:
                self.headItems = items[1:]
                heading = False
            else:
                self.connection[items[0]] = items[1:]

    def load_regions(self, path):
        for line in open(path, 'r'):
            items = line[:-1].split('\t')
            if len(items) < 4:
                break
            module = {"Name": items[1], "Comment": items[3]}
            self.modules[items[0]] = module

    def load_hierarchy(self, path):
        for line in open(path, 'r'):
            items = line[:-1].split('\t')
            if items[0] in self.modules and items[1] in self.modules:
                self.superModules[items[0]] = items[1]
                if items[1] in self.subModules:
                    sub_modules = self.subModules[items[1]]
                else:
                    sub_modules = []
                sub_modules.append(items[0])
                self.subModules[items[1]] = sub_modules

    def build(self, threshold):
        for id in self.connection:
            origin_name = self.modules[id]["Name"]
            items = self.connection[id]
            for i in range(0, len(items)):
                try:
                    if items[i].strip() == '':
                        items[i] = '0'
                    var = float(items[i])
                    if var >= threshold:
                        target_id = self.headItems[i]
                        target_name = self.modules[target_id]["Name"]
                        origin_module = self.modules[id]
                        self.create_port("Output", origin_module, origin_name, target_name)
                        target_module = self.modules[target_id]
                        self.create_port("Input", target_module, origin_name, target_name)
                        self.create_connection(id, target_id)
                except ValueError:
                    print("Cannot convert item " + str(i) + ":'" + items[i] + "' for id:" + id + ".")
                    print(items)
        self.add_hierarchy_to_modules()

    def create_port(self, type, module, origin, target):
        port_name = self.alter_module_name(origin) + "-" + self.alter_module_name(target) + "-" + type
        if "Ports" in module:
            ports = module["Ports"]
        else:
            ports = []
        ports.append(port_name)
        module["Ports"] = ports
        port = {"Name": port_name, "Module": module["Name"], "Type": type, "Shape": [10]}
        if type == "Input":
            port["Comment"] = "An input port of " + target + " for connection from " + origin
        else:
            port["Comment"] = "An output port of " + origin + " for connection to " + target
        self.ports.append(port)

    def create_connection(self, originID, targetID):
        originName = self.modules[originID]["Name"]
        targetName = self.modules[targetID]["Name"]
        connection = {}
        connectionName = originName + "-" + targetName
        connection["Name"] = connectionName
        connection["FromModule"] = originName
        connection["ToModule"] = targetName
        outputPortName = self.alter_module_name(originName) + "-" + self.alter_module_name(targetName) + "-Output"
        inputPortName = self.alter_module_name(originName) + "-" + self.alter_module_name(targetName) + "-Input"
        connection["FromPort"] = outputPortName  # self.getPath(originID) + "/" + outputPortName
        connection["ToPort"] = inputPortName  # self.getPath(targetID) + "/" + inputPortName
        connection["Comment"] = "A connection from " + originName + " to " + targetName
        self.connections.append(connection)

    @staticmethod
    def alter_module_name(name):
        return name.replace('.', '#')

    def add_hierarchy_to_modules(self):
        for moduleID in self.modules:
            module = self.modules[moduleID]
            if moduleID in self.superModules:
                module["SuperModule"] = self.superModules[moduleID]
            if moduleID in self.subModules:
                module["SubModules"] = self.subModules[moduleID]

    def get_path(self, id):
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

    def write_json(self, path, base):
        fp = open(path, 'w')
        header = {"Type": "A"}
        basename = os.path.basename(path)
        if "." in basename:
            header["Name"] = basename[0:basename.rfind(".")]
        else:
            header["Name"] = basename
        header["Base"] = base
        self.json["Header"] = header
        modules = []
        for module in self.modules:
            modules.append(self.modules[module])
        self.json["Modules"] = modules
        self.json["Ports"] = self.ports
        self.json["Connections"] = self.connections
        json.dump(self.json, fp, indent=1)
        fp.close()


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("Usage: table2brical.py connection.txt regions.txt hierarchy.txt output.json prefix threshold")
        quit()
    params = sys.argv
    threshold = float(params[6])
    t2b = Table2BriCAL()
    t2b.load_connection(params[1])
    t2b.load_regions(params[2])
    t2b.load_hierarchy(params[3])
    t2b.build(threshold)
    t2b.write_json(params[4], params[5])
