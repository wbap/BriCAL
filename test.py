#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import brical
import brica1
import numpy as np

# import component
# reload(sys)

def print_network(network):
    print("--- Disp network ---")
    for k, v in network.items():
        if len(v):
            print(k + ":")
            for k2, v2 in sorted(v.items()):
                print(k2 + "\t")
                print(v2)


if len(sys.argv) != 2:
    sys.stderr.write("Usage: test <test-dir>\n")
    exit(0)

path = sys.argv[1]
list_file = os.listdir(path)
# Load json files
network_builder = brical.NetworkBuilder()
print("--- Load file ---")
for file in sorted(list_file):
    if file[0] == "I":  # Import file
        continue
    file = path + "/" + file
    if os.path.isdir(file):  # directory
        continue
    f = open(file)
    print(file)
    if not network_builder.load_file(f):
        sys.stderr.write("ERROR: load file " + file + "\n")
        exit()
network = network_builder.get_network()

# Create agent

agent_builder = brical.AgentBuilder()
agent = agent_builder.create_agent(network_builder)
if agent == agent_builder.INCONSISTENT:
    sys.stderr.write("ERROR: INCONSISTENT!\n")
elif agent == agent_builder.NOT_GROUNDED:
    sys.stderr.write("ERROR: NOT_GROUNDED!\n")
elif agent == agent_builder.COMPONENT_NOT_FOUND:
    sys.stderr.write("ERROR: COMPONENT_NOT_FOUND!\n")
if type(agent) != brica1.Agent:
    exit()

print_network(network)

# Get modules
modules = agent_builder.get_modules()

buffers = []
print("--- Initialization ---")
for module, v in network["ModuleDictionary"].items():
    impl = v["ImplClass"]
    if impl == "":
        continue
    component = modules[module]
    ports = v["Ports"]
    buffers.append([module, component, ports])
    if "InputModule" in module:  # Setting of initial data
        l = network["Ports"][module + "." + ports[0]]["Shape"]
        data = []
        for i in range(l):
            data.append(i)
        init_data = np.array(data, dtype=np.int16)
        component.set_state(ports[0], init_data)
        print("{0}.set_state({1}, [0, 1, 2...])".format(module, ports[0]))

    if "PipeComponent" in impl:
        ip = ""
        op = ""
        for port in ports:
            if module + "." + port in network["Ports"]:
                io = network["Ports"][module + "." + port]["IO"]
                if io == "Input":
                    ip = port
                elif io == "Output":
                    op = port
            else:
                sys.stderr.write("ERROR: No port in PipeComponent!\n")
                exit()

        component.set_map(ip, op)
        print("%s.set_map({0}, {1})".format(module, ip, op))

# Run
print("--- Run ---")
scheduler = brica1.VirtualTimeSyncScheduler(agent)
for i in range(len(buffers)):
    print(scheduler.step())
    for b in buffers:
        for p in b[2]:
            if network["Ports"][b[0] + "." + p]["IO"] == "Input":
                print(b[1].get_in_port(p).buffer)
            else:
                print(b[1].get_out_port(p).buffer)
            print("{0}\t{1}".format(b[0], p))
