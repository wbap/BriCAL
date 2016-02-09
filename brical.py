#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
brical.py
=====

This module contains the class `NetworkBuilder` and `AgentkBuilder` which interprets 
the contents of BriCA language files.

"""

# BriCA Language Interpreter for V1 (Interpreter version 1)
#  Originally licenced for WBAI (wbai.jp) under the Apache License (?)
#  Created: 2016-01-31

# TODO: import, subports

import os
import sys
import numpy
import brica1
import json


debug = False #True

class NetworkBuilder:
    """
    The BriCA language interpreter.
    - reads BriCA language files.
    """
    unit_dic={}         # Map: BriCA unit name ⇒ unit object
    super_modules={}    # Super modules
#    base_name_space=""  # Base Name Space

    module_dictionary={}
    sub_modules={}
    __ports={}
    __connections={}
    __comments={}
    __network={}
    __super_sub_modules={}        # Super & Sub modules
    __load_files = []

    def __init__(self):
        """
        NetworkBuilder Create a new `NetworkBuilder` instance.
        Args:
          None.
        Returns:
          NetworkBuilder: a new `NetworkBuilder` instance.
        """
        unit_dic={}
        module_dictionary={}
        super_modules={}
        sub_modules={}
        __ports={}
        __connections={}
        __comments={}
        __load_files = []

    def load_file(self, file_object):
        """
        Load a BriCA language json file.
        Args:
          A file object
        Returns:
          success:True, failure:False
        """
        self.__load_files.append(os.path.abspath(file_object.name))
        dir_name = os.path.dirname(file_object.name)
        try:
            jsn = json.load(file_object)
        except:
            print >> sys.stderr, "ERROR: File could not be read!"
            return False

        if not "Header" in jsn:
            print >> sys.stderr, "ERROR: Header must be specified!"
            return False
        header = jsn["Header"]

        if "Import" in header:
            import_files = header["Import"]
            for import_file in import_files:
                if "/" != import_file[0]: # not full path
                    import_file = dir_name + "/" + import_file
                if not os.path.isfile(import_file):
                    print >> sys.stderr, "ERROR: JSON file %s not found!" % import_file
                    return False
                if os.path.abspath(import_file) in self.__load_files:
                    print "Import file '%s' has been read!" % import_file
                    continue
                f = open(import_file)
                if self.load_file(f) == False:
                    return False

        if not "Name" in header:
            print >> sys.stderr, "ERROR: Header name must be specified!"
            return False

        if not "Base" in header:
            print >> sys.stderr, "ERROR: Base name space must be specified!"
            return False
        self.base_name_space = header["Base"].strip()

        if not "Type" in header:
            print >> sys.stderr, "ERROR: Type must be specified!"
            return False
        self.__type=header["Type"]

        if "Comment" in header:
            self.__comments["Header." + header["Name"]] = header["Comment"]

        if self.__set_modules(jsn) == False:
            return False

        if self.__set_ports(jsn) == False:
            return False

        if self.__set_connections(jsn) == False:
            return False

        return True

        
    def get_network(self):
        """
        Args:
          None
        return:
          the network created by load_file(self, file_object)
        """
        return {"ModuleDictionary":self.module_dictionary, "SuperModules":self.super_modules,
            "SubModules":self.sub_modules, "Ports":self.__ports, "Connections":self.__connections, "Comments":self.__comments}


    def check_consistency(self):
        """
        Args:
          None
        return:
          true iff no fatal inconsistency in the network
          function:
          see the consistency check section below.
        """
        for module_name in self.module_dictionary:
            if not module_name in self.unit_dic:
                if debug:
                    print "Creating " + module_name + "."
                self.unit_dic[module_name]=brica1.Module()        # New Module instance

        # SuperModules of consistency check
        for module, superModule in self.super_modules.items():
            if not superModule in self.module_dictionary:
                print >> sys.stderr, "ERROR: Super Module '%s' is not defined!" % (superModule)
                return False
            # Loop check
            if self.__loop_check(superModule, module):
                print >> sys.stderr, "ERROR: Loop detected while trying to add " + module + " as a subunit to " + superModule + "!"
                return False

        # SubModules of consistency check
        for superModule, subModules in self.sub_modules.items():
            for subModule in subModules:
                if not subModule in self.module_dictionary:
                    print >> sys.stderr, "ERROR: Sub Module '%s' is not defined!" % (subModule)
                    return False
                # Loop check
                if self.__loop_check(superModule, subModule):
                    print >> sys.stderr, "ERROR: Loop detected while trying to add " + superModule + " as a subunit to " + subModule + "!"
                    return False

        # Port of consistency check
        for module_name in self.module_dictionary:
            ports = self.module_dictionary[module_name]["Ports"]
            if len(ports) == 0:
                print >> sys.stderr, "ERROR: The specified module '%s' does not have the port!" % module_name
                return False
            for port in ports:
                if not module_name + "." + port in self.__ports:
                    print >> sys.stderr, "ERROR: The specified module '%s' does not have the port!" % module_name
                    return False

        for port_name, v in self.__ports.items():
            # Fatal if the specified modules have not been defined.
            if not "Module" in v:
                print >> sys.stderr, "ERROR: Module is not defined in the port '%s'!" % port_name
                return False

            module_name = v["Module"]
            if not module_name in self.module_dictionary:
                print >> sys.stderr, "ERROR: Specified module '%s' is not defined in the port '%s'!" % (module_name, port_name)
                return False

            # Fatal if the shape has not been defined.
            if not "Shape" in v:
                print >> sys.stderr, "ERROR: Shape is not defined in the port '%s'!" % port_name
                return False

            length = v["Shape"]
            if length < 1:
                print >> sys.stderr, "ERROR: Incorrect length of Shape for the port '%s'!" % port_name
                return False

            # Fatal if the specified modules do not have the port, abort with a message.
            module = self.module_dictionary[module_name]
            pv = port_name.split(".")
            last_port_name = pv[len(pv) - 1]
            if not last_port_name in module["Ports"]:
                print >> sys.stderr, "ERROR: Port '%s' is not defined in the module '%s'!" % (last_port_name, module_name)
                return False

            module = self.unit_dic[module_name]
            if v["IO"] == "Input":
                module.make_in_port(last_port_name, length)
                if debug:
                    print "Creating an input port " + last_port_name + " (length " + str(length) + ") to " + module_name + "."
            elif v["IO"] == "Output":
                module.make_out_port(last_port_name, length)
                if debug:
                    print "Creating an output port " + last_port_name + " (length " + str(length) + ") to " + module_name + "."

        # Connection of consistency check
        for k, v in self.__connections.items():
            # Fatal if the specified ports have not been defined.
            if not v[0] in self.__ports:
                print >> sys.stderr, "ERROR: The specified port '%s' is not defined in connection '%s'." % (v[0], k)
                return False
            if not v[1] in self.__ports:
                print >> sys.stderr, "ERROR: The specified port '%s' is not defined in connection '%s'." % (v[1], k)
                return False

            tp = v[0].split(".")
            to_port = tp[len(tp) - 1]
            fp = v[1].split(".")
            from_port = fp[len(fp) - 1]
            to_unit = self.__ports[v[0]]["Module"]
            from_unit = self.__ports[v[1]]["Module"]

            # if from_unit & to_unit belong to the same level
            if ((not from_unit in self.__super_sub_modules) and (not to_unit in self.__super_sub_modules)) or \
                (from_unit in self.__super_sub_modules and to_unit in self.__super_sub_modules and \
                (self.__super_sub_modules[from_unit] == self.__super_sub_modules[to_unit])):
                try:
                    fr_port_obj = self.unit_dic[from_unit].get_out_port(from_port)
                    to_port_obj = self.unit_dic[to_unit].get_in_port(to_port)
                    if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                        print >> sys.stderr, "ERROR: Port dimension unmatch!"
                        return False
                    # Creating a connection
                    brica1.connect((self.unit_dic[from_unit],from_port), (self.unit_dic[to_unit],to_port))
                    if debug:
                        print "Creating a connection from " + from_port + " of " + from_unit + " to " + to_port + " of " + to_unit + "."
                except:
                    print >> sys.stderr, "ERROR: adding a connection from " + from_unit + " to " + to_unit + " on the same level but not from an output port to an input port!"
                    return False
            # else if from_unit is the direct super module of the to_unit
            elif to_unit in self.__super_sub_modules and self.__super_sub_modules[to_unit]==from_unit:
                try:
                    fr_port_obj = self.unit_dic[from_unit].get_in_port(from_port)
                    to_port_obj = self.unit_dic[to_unit].get_in_port(to_port)
                    if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                        print >> sys.stderr, "ERROR: Port dimension unmatch!"
                        return False
                    # Creating a connection (alias)
                    self.unit_dic[to_unit].alias_in_port(self.unit_dic[from_unit], from_port, to_port)
                    if debug:
                        print "Creating a connection (alias) from " + from_port + " of " + from_unit + " to " + to_port + " of " + to_unit + "."
                except:
                    print >> sys.stderr, "ERROR: Error adding a connection from the super module " + from_unit + " to " + to_unit + " but not from an input port to an input port!"
                    return False
            # else if to_unit is the direct super module of the from_unit
            elif from_unit in self.__super_sub_modules and self.__super_sub_modules[from_unit]==to_unit:
                try:
                    fr_port_obj = self.unit_dic[from_unit].get_out_port(from_port)
                    to_port_obj = self.unit_dic[to_unit].get_out_port(to_port)
                    if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                        print >> sys.stderr, "ERROR: Port dimension unmatch!"
                        return False
                    # Creating a connection (alias)
                    self.unit_dic[from_unit].alias_out_port(self.unit_dic[to_unit], to_port, from_port)
                    if debug:
                        print "Creating a connection (alias) from " + from_port + " of " + from_unit + " to " + to_port + " of " + to_unit + "."
                except:
                    print >> sys.stderr, "ERROR: Error adding a connection from " + from_unit + " to its super module " + to_unit + " but not from an output port to an output port!"
                    return False
            # else connection level error!
            else:
                print >> sys.stderr, "ERROR: Trying to add a connection between units " + from_unit + " and " + to_unit + " in a remote level!"
                return False

        return True


    def check_grounding(self):
        """
        Args:
          None
        return:
          true iff the network is grounded, i.e., every module at the bottom of the hierarchy has a component specification.  
        """
        for module_name, v in self.module_dictionary.items():
            implclass = v["ImplClass"]
            if implclass != "":
                if debug:
                    print "Use the existing ImplClass " + implclass + " for " + module_name + "."
                try:
                    component_instance = eval(implclass+'()')        # New ImplClass instance
                except:
                    v = implclass.rsplit(".", 1)
                    mod_name = v[0]
                    class_name = v[1]
                    try:
                        mod = __import__(mod_name, globals(), locals(), [class_name], -1)
                        Klass = getattr(mod, class_name)
                        component_instance = Klass()
                    except:
                        print >> sys.stderr, "ERROR: Module " + module_name + " at the bottom not grounded as a Component!"
                        return False
                try:
                    module = self.unit_dic[module_name]
                    module.add_component(module_name, component_instance)
                    for port in module.in_ports:
                        length=module.get_in_port(port).buffer.shape[0]
                        component_instance.make_in_port(port, length)
                        component_instance.alias_in_port(module, port, port)
                    for port in module.out_ports:
                        length=module.get_out_port(port).buffer.shape[0]
                        component_instance.make_out_port(port, length)
                        component_instance.alias_out_port(module, port, port)
                except:
                    print >> sys.stderr, "ERROR: Module " + module_name + " at the bottom not grounded as a Component!"
                    return False
        return True


    def __set_modules(self, jsn):
        """ Add modules from the JSON description
        Args:
          None
        Returns:
          None
        """
        if "Modules" in jsn:
            modules = jsn["Modules"]
            for module in modules:
                if self.__set_a_module(module) == False:
                    return False
        else:
            print >> sys.stderr, "Warning: No `Modules` in the language file."

        return True


    def __set_a_module(self, module):
        if not "Name" in module:
            print >> sys.stderr, "ERROR: Module name must be specified!"
            return False

        module_name = module["Name"].strip()
        if module_name == "":
            print >> sys.stderr, "ERROR: Module name must be specified!"
            return False
        module_name = self.__prefix_base_name_space(module_name)                # Prefixing the base name space

        defined_module = None
        if module_name in self.module_dictionary:
            defined_module = self.module_dictionary[module_name]

        ports = []
        if "Ports" in module:
            ports = module["Ports"]
        # Multiple registration
        if defined_module:
            for p in defined_module["Ports"]:
                if not p in ports:
                    ports.append(p)

        implclass = ""
        if "ImplClass" in module:
            # if an implementation class is specified
            implclass = module["ImplClass"].strip()
        elif self.__type == "C":
            print >> sys.stderr, "ERROR: ImplClass is necessary if the type C in the module " +  module_name + "!"
            return False
        # Multiple registration
        if defined_module:
            if implclass == "":
                implclass = defined_module["ImplClass"]
            else:
                if defined_module["ImplClass"] != "":
                    print "ImplClass '%s' of '%s' is replaced with '%s'." % (defined_module["ImplClass"], module_name, implclass)

        self.module_dictionary[module_name] = {"Ports":ports, "ImplClass":implclass}

        supermodule = ""
        if "SuperModule" in module:
            supermodule = module["SuperModule"].strip()
            supermodule = self.__prefix_base_name_space(supermodule)
        if supermodule != "" :
            # Multiple registration
            if module_name in self.super_modules:
                print "Super module '%s' of '%s' is replaced with '%s'." % (self.super_modules[module_name], module_name, supermodule)
            self.super_modules[module_name] = supermodule
            self.__super_sub_modules[module_name] = supermodule

        if "SubModules" in module:
            for submodule in module["SubModules"]:
                if submodule != "":
                    submodule = self.__prefix_base_name_space(submodule)
                    if not module_name in self.sub_modules:
                        self.sub_modules[module_name] = []
                    self.sub_modules[module_name].append(submodule)
                    self.__super_sub_modules[submodule] = module_name

        if "Comment" in module:
            self.__comments["Modules." + module_name] = module["Comment"]

        return True


    def __prefix_base_name_space(self, name):
        if name.find(".")<0:
            return self.base_name_space + "." + name
        else:
            return name


    def __loop_check(self, superunit, subunit):
        if superunit == subunit:
           return True
        val = superunit
        while val in self.__super_sub_modules:
            val = self.__super_sub_modules[val]
            if val == subunit:
                return True

        return False


    def __set_ports(self, jsn):
        """ Add ports from the JSON description
        Args:
          None
        Returns:
          None
        """
        if "Ports" in jsn:
            ports = jsn["Ports"]
            for port in ports:
                if self.__set_a_port(port) == False:
                    return False
        else:
            print >> sys.stderr, "Warning: No `Ports` in the language file."

        return True


    def __set_a_port(self, port):
        if "Name" in port:
            port_name = port["Name"].strip()
        else:
            print >> sys.stderr, "ERROR: Name not specified while adding a port!"
            return False

        if "Module"in port:
            port_module = port["Module"].strip()
            port_module = self.__prefix_base_name_space(port_module)
        else:
            print >> sys.stderr, "ERROR: Module not specified while adding a port!"
            return False
        port_name = port_module + "." + port_name

        defined_port = None
        if port_name in self.__ports:
            defined_port = self.__ports[port_name]

        # Multiple registration
        if defined_port:
		if port_module != defined_port["Module"]:
                    print >> sys.stderr, "ERROR: Module '%s' defined in the port '%s' is already defined as a module '%s'." \
                        % (port_module, port_name, self.__ports[port_name]["Module"])
                    return False

        if "Type" in port:
            port_type = port["Type"].strip()
            if port_type != "Input" and port_type != "Output":
                print >> sys.stderr, "ERROR: Invalid port type '%s'!" % port_type
                return False
            elif defined_port and port_type != defined_port["IO"]:
                print >> sys.stderr, "ERROR: The port type of port '%s' differs from previously defined port type!" % port_name
                return False
        else:
            print >> sys.stderr, "ERROR: Type not specified while adding a port!"
            return False

        if "Shape" in port:
            shape = port["Shape"]
            if len(shape) != 1:
                print >> sys.stderr, "ERROR: Shape supports only one-dimensional vector!"
                return False
            if not isinstance(shape[0], int):
                print >> sys.stderr, "ERROR: The value of the port is not a number!"
                return False
            if int(shape[0]) < 1:
                print >> sys.stderr, "ERROR: Port dimension < 1!"
                return False
            self.__ports[port_name] = {"IO":port_type, "Module":port_module, "Shape":shape[0]}
        else:
            self.__ports[port_name] = {"IO":port_type, "Module":port_module}

        if "Comment" in port:
            self.__comments["Ports." + port_name] = port["Comment"]

        return True


    def __set_connections(self, jsn):
        """ Add connections from the JSON description
        Args:
          None
        Returns:
          None
        """
        if "Connections" in jsn:
            connections = jsn["Connections"]
            for connection in connections:
                if self.__set_a_connection(connection) == False:
                    return False
        else:
            if self.__type!="C":
                print >> sys.stderr, "Warning: No `Connections` in the language file."

        return True


    def __set_a_connection(self, connection):
        if "Name" in connection:
            connection_name = connection["Name"]
        else:
            print >> sys.stderr, "ERROR: Name not specified while adding a connection!"
            return False

        defined_connection = None
        if connection_name in self.__connections:
            defined_connection = self.__connections[connection_name]

        if "FromModule" in connection:
            from_unit = connection["FromModule"]
            from_unit = self.__prefix_base_name_space(from_unit)
        else:
            print >> sys.stderr, "ERROR: FromModule not specified while adding a connection!"
            return False
        if "FromPort" in connection:
            from_port = connection["FromPort"]
        else:
            print >> sys.stderr, "ERROR: FromPort not specified while adding a connection!"
            return False
        if "ToModule"in connection:
            to_unit = connection["ToModule"]
            to_unit = self.__prefix_base_name_space(to_unit)
        else:
            print >> sys.stderr, "ERROR: ToModule not specified while adding a connection!"
            return False
        if "ToPort" in connection:
            to_port = connection["ToPort"]
        else:
            print >> sys.stderr, "ERROR: ToPort not specified while adding a connection!"
            return False
        
        # Multiple registration
        if defined_connection and defined_connection[0] != to_unit + "." + to_port:
            print >> sys.stderr, "ERROR: Defined port '%s' is different from the previous ones in connection '%s'!" % (to_unit + "." + to_port, connection_name)
            return False
        if defined_connection and defined_connection[1] != from_unit + "." + from_port:
            print >> sys.stderr, "ERROR: Defined port '%s' is different from the previous ones in connection '%s'!" % (from_unit + "." + from_port, connection_name)
            return False

        if "Comment" in connection:
            self.__comments["Connections." + connection_name] = connection["Comment"]

        self.__connections[connection_name] = (to_unit + "." + to_port, from_unit + "." + from_port)
        return True


class AgentBuilder:
    """
    The BriCA language interpreter.
    - creates a BriCA agent based on the file contents.
    """
    def __init__(self):
        self.INCONSISTENT = 1
        self.NOT_GROUNDED = 2
        self.COMPONENT_NOT_FOUND = 3
        self.unit_dic = None

    def create_agent(self, scheduler, network):
        if network.check_consistency() == False:
            return self.INCONSISTENT

        if network.check_grounding() == False:
            return self.NOT_GROUNDED

        for module, super_module in network.super_modules.items():
            if super_module in network.module_dictionary:
                network.unit_dic[super_module].add_submodule(module, network.unit_dic[module])
                if debug:
                    print "Adding a module " + module + " to " + super_module + "."

        # Main logic
        top_module = brica1.Module()
        for unit_key in network.unit_dic.keys():
            if not unit_key in network.super_modules:
                if isinstance(network.unit_dic[unit_key], brica1.Module):
                    top_module.add_submodule(unit_key, network.unit_dic[unit_key])
                    if debug:
                        print "Adding a module " + unit_key + " to a BriCA agent."
        agent = brica1.Agent(scheduler)
        agent.add_submodule("__Runtime_Top_Module", top_module)
        self.unit_dic = network.unit_dic
        return agent

    def get_modules(self):
        return self.unit_dic
