#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import brical
import brica1
import numpy as np
#import component
reload(sys)
sys.setdefaultencoding('utf-8')
#module = eval("component.ConstantComponent2()")
#print module

def print_network(network):
    print "--- Disp network ---"
    for k, v in network.items():
        if len(v):
            print k + ":"
            for k2, v2 in sorted(v.items()):
                print k2 + "\t",
                print v2


if len(sys.argv) != 2:
    print >> sys.stderr, "Usage: test <test-dir>"
    exit(0)

path = sys.argv[1]
list_file = os.listdir(path)
# Load json files
network_builder = brical.NetworkBuilder()
print "--- Load file ---"
for file in sorted(list_file):
    if file[0] == "I": # Import file
        continue
    file = path + "/" + file
    if os.path.isdir(file) == True: # directory
        continue
    f = open(file)
    print file
    if network_builder.load_file(f) == False:
        print >> sys.stderr, "ERROR: load file " + file
        exit()
network = network_builder.get_network()

# Create agent
scheduler = brica1.VirtualTimeSyncScheduler()
agent_builder = brical.AgentBuilder()
agent = agent_builder.create_agent(scheduler, network_builder)
if agent == agent_builder.INCONSISTENT:
    print >> sys.stderr, "ERROR: INCONSISTENT!"
elif agent == agent_builder.NOT_GROUNDED:
    print >> sys.stderr, "ERROR: NOT_GROUNDED!"
elif agent == agent_builder.COMPONENT_NOT_FOUND:
    print >> sys.stderr, "ERROR: COMPONENT_NOT_FOUND!"
if type(agent) != brica1.Agent:
    exit()

print_network(network)

# Get modules
modules = agent_builder.get_modules()

buffers = []
print "--- Initialization ---"
for module, v in network["ModuleDictionary"].items():
    impl = v["ImplClass"]
    if impl != "":
        component = modules[module].get_component(module)
        ports = v["Ports"]
        buffers.append([module, component, ports])
    if "InputModule" in module:
        # Setting of initial data
	l = network["Ports"][module + "." + ports[0]]["Shape"]
        data = []
        for i in range(l):
            data.append(i)
        init_data = np.array(data, dtype=np.int16)
        component.set_state(ports[0], init_data)
	print "%s.set_state(%s, [0, 1, 2...])" % (module, ports[0]) 
        
    if "PipeComponent" in impl:
        ip = ""
        op = ""
        for port in ports:
            if module + "." + port in network["Ports"]:
                io = network["Ports"][module + "." + port]["IO"]
                if io  == "Input":
                    ip = port
                elif io  == "Output":
                    op = port
            else:
                print >> sys.stderr, "ERROR: No port in PipeComponent!"
                exit()

        component.set_map(ip, op)
	print "%s.set_map(%s, %s)" % (module, ip, op) 

# Run
print "--- Run ---"
for i in range(len(buffers)):
    print agent.step()
    for b in buffers:
        for p in b[2]:
            if network["Ports"][b[0] + "." + p]["IO"] == "Input":
                print b[1].get_in_port(p).buffer,
            else:
                print b[1].get_out_port(p).buffer,
            print "%s\t%s" % (b[0], p)
