#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
brical.py
=====

This module contains the class `NetworkBuilder` and `AgentBuilder` which interprets 
the contents of BriCA language files.

"""

# BriCA Language Interpreter for V1 (Interpreter version 1)
#  Originally licenced for WBAI (wbai.jp) under the Apache License
#  Recreated: 2022-02

import os
import sys
import brica1
import json

debug = False  # True


class NetworkBuilder:
    """
    The BriCA language interpreter.
    - reads BriCA language files.
    """

    def __init__(self):
        """
        NetworkBuilder Create a new `NetworkBuilder` instance.
        Args:
          None.
        Returns:
          NetworkBuilder: a new `NetworkBuilder` instance.
        """
        self.__ports = {}
        self.__connections = {}
        self.__comments = {}
        self.__load_files = []
        self.base_name_space = ""
        self.__type = ""
        self.__connections_from_to = {}
        self.__alias_in = {}
        self.__alias_out = {}
        self.unit_dic = {}  # Map: BriCA unit name ⇒ unit object
        self.super_modules = {}  # Super modules
        self.module_dictionary = {}
        self.sub_modules = {}
        self.__ports = {}
        self.__connections = {}
        self.__comments = {}
        self.__network = {}
        self.__super_sub_modules = {}  # Super & Sub modules
        self.__sub_super_modules = {}  # Super & Sub modules
        self.__load_files = []

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
        except IOError:
            sys.stderr.write("ERROR: File could not be read!\n")
            return False

        if "Header" not in jsn:
            sys.stderr.write("ERROR: Header must be specified!\n")
            return False
        header = jsn["Header"]

        if "Import" in header:
            import_files = header["Import"]
            for import_file in import_files:
                if "/" != import_file[0]:  # not full path
                    import_file = dir_name + "/" + import_file
                if not os.path.isfile(import_file):
                    sys.stderr.write("ERROR: JSON file {0} not found!\n".format(import_file))
                    return False
                if os.path.abspath(import_file) in self.__load_files:
                    print("Import file {0} has been read!\n".format(import_file))
                    continue
                f = open(import_file)
                if not self.load_file(f):
                    return False

        if "Name" not in header:
            sys.stderr.write("ERROR: Header name must be specified!\n")
            return False

        if "Base" not in header:
            sys.stderr.write("ERROR: Base name space must be specified!\n")
            return False
        self.base_name_space = header["Base"].strip()

        if "Type" not in header:
            sys.stderr.write("ERROR: Type must be specified!\n")
            return False
        self.__type = header["Type"]

        if "Comment" in header:
            self.__comments["Header." + header["Name"]] = header["Comment"]

        if not self.__set_modules(jsn):
            return False

        if not self.__set_ports(jsn):
            return False

        if not self.__set_connections(jsn):
            return False

        return True

    def get_network(self):
        """
        Args:
        return:
          the network created by load_file(self, file_object)
        """
        return {"ModuleDictionary": self.module_dictionary, "SuperModules": self.super_modules,
                "SubModules": self.sub_modules, "Ports": self.__ports, "Connections": self.__connections,
                "Comments": self.__comments}

    def check_consistency(self):
        """
        Args:
        return:
          true iff no fatal inconsistency in the network
          function:
          see the consistency check section below.
        """
        for module_name in self.module_dictionary:
            if module_name not in self.unit_dic:
                if debug:
                    print("Creating " + module_name + ".")
                self.unit_dic[module_name] = brica1.Module()  # New Module instance

        # SuperModule consistency check
        for module, superModule in self.super_modules.items():
            if superModule not in self.module_dictionary:
                sys.stderr.write("ERROR: Super Module {0} is not defined!\n".format(superModule))
                return False
            # Loop check
            if self.__loop_check(superModule, module):
                sys.stderr.write(
                    "ERROR: Loop detected while trying to add " + module + " as a subunit to " + superModule + "!\n")
                return False

        # SubModule consistency check
        for superModule, subModules in self.sub_modules.items():
            for subModule in subModules:
                if subModule not in self.module_dictionary:
                    sys.stderr.write("ERROR: Sub Module {0} is not defined!\n".format(subModule))
                    return False
                # Loop check
                if self.__loop_check(superModule, subModule):
                    sys.stderr.write(
                        "ERROR: Loop detected while trying to add " + superModule + " as a subunit to "
                        + subModule + "!\n")
                    return False

        # Port consistency check
        for module_name in self.module_dictionary:
            ports = self.module_dictionary[module_name]["Ports"]
            if len(ports) == 0:
                sys.stderr.write("ERROR: The specified module {0} does not have the port!\n".format(module_name))
                return False
            for port in ports:
                if not module_name + "." + port in self.__ports:
                    sys.stderr.write("ERROR: The specified module {0} does not have the port!\n".format(module_name))
                    return False

        for port_name, v in self.__ports.items():
            # Fatal if the specified modules have not been defined.
            if "Module" not in v:
                sys.stderr.write("ERROR: Module is not defined in the port {0}!\n".format(port_name))
                return False

            module_name = v["Module"]
            if module_name not in self.module_dictionary:
                sys.stderr.write(
                    "ERROR: Specified module {0} is not defined in the port {1}!\n".format(module_name, port_name))
                return False

            # Fatal if the shape has not been defined.
            if "Shape" not in v:
                sys.stderr.write("ERROR: Shape is not defined in the port {0}!\n".format(port_name))
                return False

            length = v["Shape"]
            if length < 1:
                sys.stderr.write("ERROR: Incorrect length of Shape for the port {0}!\n".format(port_name))
                return False

            # Fatal if the specified modules do not have the port, abort with a message.
            module = self.module_dictionary[module_name]
            pv = port_name.split(".")
            last_port_name = pv[len(pv) - 1]
            if last_port_name not in module["Ports"]:
                sys.stderr.write("ERROR: Port {0} is not defined in the module {1}!\n"
                                 .format(last_port_name, module_name))
                return False

            module = self.unit_dic[module_name]
            if v["IO"] == "Input":
                module.make_in_port(last_port_name, length)
                if debug:
                    print("Creating an input port " + last_port_name + " (length " + str(
                        length) + ") to " + module_name + ".")
            elif v["IO"] == "Output":
                module.make_out_port(last_port_name, length)
                if debug:
                    print("Creating an output port " + last_port_name + " (length " + str(
                        length) + ") to " + module_name + ".")

        # Connection consistency check
        for k, v in self.__connections.items():
            # Fatal if the specified ports have not been defined.
            if not v[0] in self.__ports:
                sys.stderr.write("ERROR: The specified port {0} is not defined in connection {1}.\n".format(v[0], k))
                return False
            if not v[1] in self.__ports:
                sys.stderr.write("ERROR: The specified port {0} is not defined in connection {1}.\n".format(v[1], k))
                return False

            tp = v[0].split(".")
            to_port = tp[len(tp) - 1]
            fp = v[1].split(".")
            from_port = fp[len(fp) - 1]
            to_unit = self.__ports[v[0]]["Module"]
            from_unit = self.__ports[v[1]]["Module"]

            # if from_unit & to_unit belong to the same level
            if (from_unit not in self.__super_sub_modules) and (to_unit not in self.__super_sub_modules) or \
                    (from_unit in self.__super_sub_modules and to_unit in self.__super_sub_modules and
                     (self.__super_sub_modules[from_unit] == self.__super_sub_modules[to_unit])):
                try:
                    fr_port_obj = self.unit_dic[from_unit].get_out_port(from_port)
                    to_port_obj = self.unit_dic[to_unit].get_in_port(to_port)
                    if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                        sys.stderr.write("ERROR: Port dimension unmatched!\n")
                        return False
                    # Registering a connection
                    self.__connections_from_to[from_unit + ":" + to_unit] = (from_port, to_port)
                    if debug:
                        print(
                            "Creating a connection from " + from_port + " of " + from_unit + " to " + to_port +
                            " of " + to_unit + ".\n")
                except KeyError:
                    sys.stderr.write(
                        "ERROR: adding a connection from " + from_unit + " to " + to_unit +
                        " on the same level but not from an output port to an input port!\n")
                    return False
            # else if from_unit is the direct super module of the to_unit
            elif to_unit in self.__super_sub_modules and self.__super_sub_modules[to_unit] == from_unit:
                try:
                    fr_port_obj = self.unit_dic[from_unit].get_in_port(from_port)
                    to_port_obj = self.unit_dic[to_unit].get_in_port(to_port)
                    if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                        sys.stderr.write("ERROR: Port dimension unmatched!\n")
                        return False
                    # Registering a connection (alias)
                    self.__alias_in[from_unit + ":" + to_unit] = (from_port, to_port)
                    if debug:
                        print(
                            "Creating a connection (alias) from " + from_port + " of " + from_unit + " to "
                            + to_port + " of " + to_unit + ".")
                except KeyError:
                    sys.stderr.write(
                        "ERROR: Error adding a connection from the super module " + from_unit + " to " + to_unit +
                        " but not from an input port to an input port!\n")
                    return False
            # else if to_unit is the direct super module of the from_unit
            elif from_unit in self.__super_sub_modules and self.__super_sub_modules[from_unit] == to_unit:
                try:
                    fr_port_obj = self.unit_dic[from_unit].get_out_port(from_port)
                    to_port_obj = self.unit_dic[to_unit].get_out_port(to_port)
                    if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                        sys.stderr.write("ERROR: Port dimension unmatched!\n")
                        return False
                    # Registering a connection (alias)
                    self.__alias_out[from_unit + ":" + to_unit] = (from_port, to_port)
                    if debug:
                        print(
                            "Creating a connection (alias) from " + from_port + " of " + from_unit + " to " + to_port +
                            " of " + to_unit + ".\n")
                except KeyError:
                    sys.stderr.write(
                        "ERROR: Error adding a connection from " + from_unit + " to its super module " + to_unit
                        + " but not from an output port to an output port!")
                    return False
            # else connection level error!
            else:
                sys.stderr.write(
                    "ERROR: Trying to add a connection between units " + from_unit + " and " + to_unit +
                    " in a remote level!\n")
                return False

        return True

    def check_grounding(self):
        """
        Args:
        return:
          true iff the network is grounded, i.e., every module at the bottom of the hierarchy has
          a component specification.
        """
        return_value = True
        for module_name, v in self.module_dictionary.items():
            if module_name in self.__sub_super_modules:
                continue
            implclass = v["ImplClass"]
            if implclass == "":
                sys.stderr.write("ERROR: Module " + module_name
                                 + " at the bottom but ImplClass not specified!\n")
                return_value = False
            else:
                if debug:
                    print("Use the existing ImplClass " + implclass + " for " + module_name + ".")
                try:
                    self.unit_dic[module_name] = eval(implclass + '()')  # New ImplClass instance
                except (ValueError, SyntaxError):
                    v = implclass.rsplit(".", 1)
                    mod_name = v[0]
                    class_name = v[1]
                    try:
                        mod = __import__(mod_name, globals(), locals(), [class_name], -1)
                        klass = getattr(mod, class_name)
                        self.unit_dic[module_name] = klass()
                    except AttributeError:
                        sys.stderr.write("ERROR: Module " + module_name
                                         + " at the bottom not grounded as a Component!\n")
                        return_value = False
            try:
                ports = self.module_dictionary[module_name]['Ports']
                for port_name in ports:
                    full_port_name = module_name + "." + port_name
                    port_v = self.__ports[full_port_name]
                    self.__make_a_port(module_name, port_v['IO'], port_name, port_v['Shape'])
            except KeyError:
                sys.stderr.write("ERROR: Module " + module_name + " at the bottom not grounded as a Component!\n")
                return False
        return return_value

    def make_connections(self, module_name, sub_modules):
        for sub_module in sub_modules:
            if module_name is not None:     # super-module
                module_names = module_name + ":" + sub_module
                if module_names in self.__alias_in:
                    from_port, to_port = self.__alias_in[module_names]
                    self.unit_dic[sub_module].alias_in_port(self.unit_dic[module_name], from_port, to_port)
                module_names = sub_module + ":" + module_name
                if module_names in self.__alias_out:
                    from_port, to_port = self.__alias_out[module_names] # from_port: sub / to_port: upper
                    self.unit_dic[sub_module].alias_out_port(self.unit_dic[module_name], to_port, from_port)
            for sub_module2 in sub_modules:
                if sub_module2 != sub_module:
                    module_names = sub_module + ":" + sub_module2
                    if module_names in self.__connections_from_to:
                        from_port, to_port = self.__connections_from_to[module_names]
                        brica1.connect((self.unit_dic[sub_module], from_port), (self.unit_dic[sub_module2], to_port))
            if sub_module in self.__sub_super_modules:
                self.make_connections(sub_module, self.__sub_super_modules[sub_module])   # recursive call

    def __make_a_port(self, module_name, io, port_name, shape):
        module = self.unit_dic[module_name]
        if io == "Input":
            module.make_in_port(port_name, shape)
            if debug:
                print("Creating an input port " + port_name + " (length " + str(
                    shape) + ") to " + module_name + ".")
        elif io == "Output":
            module.make_out_port(port_name, shape)
            if debug:
                print("Creating an output port " + port_name + " (length " + str(
                    shape) + ") to " + module_name + ".")

    def __set_modules(self, jsn):
        """ Add modules from the JSON description
        Args:
        Returns:
          None
        """
        if "Modules" in jsn:
            modules = jsn["Modules"]
            for module in modules:
                if not self.__set_a_module(module):
                    return False
        else:
            sys.stderr.write("Warning: No `Modules` in the language file.\n")

        return True

    def __set_a_module(self, module):
        if "Name" not in module:
            sys.stderr.write("ERROR: Module name must be specified!\n")
            return False

        module_name = module["Name"].strip()
        if module_name == "":
            sys.stderr.write("ERROR: Module name must be specified!\n")
            return False
        module_name = self.__prefix_base_name_space(module_name)  # Prefixing the base name space

        defined_module = None
        if module_name in self.module_dictionary:
            defined_module = self.module_dictionary[module_name]

        ports = []
        if "Ports" in module:
            ports = module["Ports"]
        # Multiple registration
        if defined_module:
            for p in defined_module["Ports"]:
                if p not in ports:
                    ports.append(p)

        implclass = ""
        if "ImplClass" in module:
            # if an implementation class is specified
            implclass = module["ImplClass"].strip()
        elif self.__type == "C":
            sys.stderr.write("ERROR: ImplClass is necessary if the type C in the module " + module_name + "!\n")
            return False
        # Multiple registration
        if defined_module:
            if implclass == "":
                implclass = defined_module["ImplClass"]
            else:
                if defined_module["ImplClass"] != "":
                    print("ImplClass '%s' of '%s' is replaced with '%s'." % (
                        defined_module["ImplClass"], module_name, implclass))

        self.module_dictionary[module_name] = {"Ports": ports, "ImplClass": implclass}

        supermodule = ""
        if "SuperModule" in module:
            supermodule = module["SuperModule"].strip()
            supermodule = self.__prefix_base_name_space(supermodule)
        if supermodule != "":
            # Multiple registration
            if module_name in self.super_modules:
                print("Super module '%s' of '%s' is replaced with '%s'." % (
                    self.super_modules[module_name], module_name, supermodule))
            self.super_modules[module_name] = supermodule
            self.__super_sub_modules[module_name] = supermodule
            if supermodule not in self.__sub_super_modules:
                self.__sub_super_modules[supermodule] = []
            self.__sub_super_modules[supermodule].append(module_name)

        if "SubModules" in module:
            for submodule in module["SubModules"]:
                if submodule != "":
                    submodule = self.__prefix_base_name_space(submodule)
                    if module_name not in self.sub_modules:
                        self.sub_modules[module_name] = []
                    self.sub_modules[module_name].append(submodule)
                    self.__super_sub_modules[submodule] = module_name
                    if module_name not in self.__sub_super_modules[module_name]:
                        self.__sub_super_modules[module_name] = []
                    if submodule not in self.__sub_super_modules[module_name]:
                        self.__sub_super_modules[module_name].append(submodule)

        if "Comment" in module:
            self.__comments["Modules." + module_name] = module["Comment"]

        return True

    def __prefix_base_name_space(self, name):
        if name.find(".") < 0:
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
        Returns:
          None
        """
        if "Ports" in jsn:
            ports = jsn["Ports"]
            for port in ports:
                if not self.__set_a_port(port):
                    return False
        else:
            sys.stderr.write("Warning: No `Ports` in the language file.\n")

        return True

    def __set_a_port(self, port):
        if "Name" in port:
            port_name = port["Name"].strip()
        else:
            sys.stderr.write("ERROR: Name not specified while adding a port!\n")
            return False

        if "Module" in port:
            port_module = port["Module"].strip()
            port_module = self.__prefix_base_name_space(port_module)
        else:
            sys.stderr.write("ERROR: Module not specified while adding a port!\n")
            return False
        port_name = port_module + "." + port_name

        defined_port = None
        if port_name in self.__ports:
            defined_port = self.__ports[port_name]

        # Multiple registration
        if defined_port:
            if port_module != defined_port["Module"]:
                sys.stderr.write("ERROR: Module {0} defined in the port {1} is already defined as a module {2}.\n"
                                 .format(port_module, port_name, self.__ports[port_name]["Module"]))
                return False

        if "Type" in port:
            port_type = port["Type"].strip()
            if port_type != "Input" and port_type != "Output":
                sys.stderr.write("ERROR: Invalid port type {0}!\n".format(port_type))
                return False
            elif defined_port and port_type != defined_port["IO"]:
                sys.stderr.write(
                    "ERROR: The port type of port {0} differs from previously defined port type!\n".format(port_name))
                return False
        else:
            sys.stderr.write("ERROR: Type not specified while adding a port!\n")
            return False

        if "Shape" in port:
            shape = port["Shape"]
            if len(shape) != 1:
                sys.stderr.write("ERROR: Shape supports only one-dimensional vector!\n")
                return False
            if not isinstance(shape[0], int):
                sys.stderr.write("ERROR: The value of the port is not a number!\n")
                return False
            if int(shape[0]) < 1:
                sys.stderr.write("ERROR: Port dimension < 1!\n")
                return False
            self.__ports[port_name] = {"IO": port_type, "Module": port_module, "Shape": shape[0]}
        else:
            self.__ports[port_name] = {"IO": port_type, "Module": port_module}

        if "Comment" in port:
            self.__comments["Ports." + port_name] = port["Comment"]

        return True

    def __set_connections(self, jsn):
        """ Add connections from the JSON description
        Args:
        Returns:
          None
        """
        if "Connections" in jsn:
            connections = jsn["Connections"]
            for connection in connections:
                if not self.__set_a_connection(connection):
                    return False
        else:
            if self.__type != "C":
                sys.stderr.write("Warning: No `Connections` in the language file.\n")

        return True

    def __set_a_connection(self, connection):
        if "Name" in connection:
            connection_name = connection["Name"]
        else:
            sys.stderr.write("ERROR: Name not specified while adding a connection!\n")
            return False

        defined_connection = None
        if connection_name in self.__connections:
            defined_connection = self.__connections[connection_name]

        if "FromModule" in connection:
            from_unit = connection["FromModule"]
            from_unit = self.__prefix_base_name_space(from_unit)
        else:
            sys.stderr.write("ERROR: FromModule not specified while adding a connection!\n")
            return False
        if "FromPort" in connection:
            from_port = connection["FromPort"]
        else:
            sys.stderr.write("ERROR: FromPort not specified while adding a connection!\n")
            return False
        if "ToModule" in connection:
            to_unit = connection["ToModule"]
            to_unit = self.__prefix_base_name_space(to_unit)
        else:
            sys.stderr.write("ERROR: ToModule not specified while adding a connection!\n")
            return False
        if "ToPort" in connection:
            to_port = connection["ToPort"]
        else:
            sys.stderr.write("ERROR: ToPort not specified while adding a connection!\n")
            return False

        # Multiple registration
        if defined_connection and defined_connection[0] != to_unit + "." + to_port:
            sys.stderr.write("ERROR: Defined port {0} is different from the previous ones in connection {1}!\n".format(
                to_unit + "." + to_port, connection_name))
            return False
        if defined_connection and defined_connection[1] != from_unit + "." + from_port:
            sys.stderr.write("ERROR: Defined port {0} is different from the previous ones in connection {1}!\n".format(
                from_unit + "." + from_port, connection_name))
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

    def create_agent(self, network):
        if not network.check_consistency():
            return self.INCONSISTENT

        if not network.check_grounding():
            return self.NOT_GROUNDED

        for module, super_module in network.super_modules.items():
            if super_module in network.module_dictionary:
                if isinstance(network.unit_dic[module], brica1.Component):
                    network.unit_dic[super_module].add_component(module, network.unit_dic[module])
                elif isinstance(network.unit_dic[module], brica1.Module):
                    network.unit_dic[super_module].add_submodule(module, network.unit_dic[module])
                if debug:
                    print("Adding a module " + module + " to " + super_module + ".")

        # Main logic

        agent = brica1.Agent()
        sub_modules = []
        for unit_key in network.unit_dic.keys():
            if unit_key not in network.super_modules:   # top level
                if isinstance(network.unit_dic[unit_key], brica1.Component):
                    agent.add_component(unit_key, network.unit_dic[unit_key])
                elif isinstance(network.unit_dic[unit_key], brica1.Module):
                    agent.add_submodule(unit_key, network.unit_dic[unit_key])
                sub_modules.append(unit_key)
                if debug:
                    print("Adding a module " + unit_key + " to a BriCA agent.")
        network.make_connections(None, sub_modules)
        self.unit_dic = network.unit_dic
        return agent

    def get_modules(self):
        return self.unit_dic
