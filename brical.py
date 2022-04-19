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
        self.super_module = {}  # Sub ⇒ Super modules
        self.sub_modules = {}  # Super ⇒ Sub modules
        self.module_dictionary = {}
        self.__network = {}
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
        return {"ModuleDictionary": self.module_dictionary, "SuperModules": self.super_module,
                "SubModules": self.sub_modules, "Ports": self.__ports, "Connections": self.__connections,
                "Comments": self.__comments}

    def upper_p(self, module1, module2):
        if module2 in self.super_module:
            upper = self.super_module[module2]
            if module1 == upper:
                return True
            else:
                if self.upper_p(module1, upper):
                    return True
                else:
                    return False
        else:
            return False

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
        for module, superModule in self.super_module.items():
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
                sys.stderr.write("ERROR: The specified module {0} does not have ports!\n".format(module_name))
                return False
            for port in ports:
                if not module_name + "." + port in self.__ports:
                    sys.stderr.write("ERROR: The specified module {0} does not have the port  {1}!\n".
                                     format(module_name, port))
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
            for connection in v:
                # Fatal if the specified ports have not been defined.
                if not connection[0] in self.__ports:
                    sys.stderr.write("ERROR: The specified port {0} is not defined in connection {1}.\n"
                                     .format(connection[0], k))
                    return False
                if not connection[1] in self.__ports:
                    sys.stderr.write("ERROR: The specified port {0} is not defined in connection {1}.\n"
                                     .format(connection[1], k))
                    return False

                tp = connection[0].split(".")
                to_port = tp[len(tp) - 1]
                fp = connection[1].split(".")
                from_port = fp[len(fp) - 1]
                to_unit = self.__ports[connection[0]]["Module"]
                from_unit = self.__ports[connection[1]]["Module"]

                # else if from_unit is an upper module of to_unit
                if self.upper_p(from_unit, to_unit):
                    try:
                        fr_port_obj = self.unit_dic[from_unit].get_in_port(from_port)
                        to_port_obj = self.unit_dic[to_unit].get_in_port(to_port)
                        if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                            sys.stderr.write("ERROR: Port dimension unmatched!\n")
                            return False
                        # Registering a connection (alias)
                        key = from_unit + ":" + to_unit
                        if key not in self.__alias_in:
                            self.__alias_in[key] = []
                        self.__alias_in[key].append((from_port, to_port))
                        if debug:
                            print(
                                "Creating a connection (alias) from " + from_port + " of " + from_unit + " to "
                                + to_port + " of " + to_unit + ".")
                    except KeyError:
                        sys.stderr.write(
                            "ERROR: Error adding a connection from the super module " + from_unit + " to " + to_unit +
                            " but not from an input port to an input port!\n")
                        return False
                # else if to_unit is an upper module of from_unit
                elif self.upper_p(to_unit, from_unit):
                    try:
                        fr_port_obj = self.unit_dic[from_unit].get_out_port(from_port)
                        to_port_obj = self.unit_dic[to_unit].get_out_port(to_port)
                        if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                            sys.stderr.write("ERROR: Port dimension unmatched!\n")
                            return False
                        # Registering a connection (alias)
                        key = from_unit + ":" + to_unit
                        if key not in self.__alias_out:
                            self.__alias_out[key] = []
                        self.__alias_out[key].append((from_port, to_port))
                        if debug:
                            print(
                                "Creating a connection (alias) from " + from_port + " of " + from_unit + " to " +
                                to_port + " of " + to_unit + ".\n")
                    except KeyError:
                        sys.stderr.write(
                            "ERROR: Error adding a connection from " + from_unit + " to its super module " + to_unit
                            + " but not from an output port to an output port!")
                        return False
                # else two modules are not in inclusion relation
                else:
                    try:
                        fr_port_obj = self.unit_dic[from_unit].get_out_port(from_port)
                        to_port_obj = self.unit_dic[to_unit].get_in_port(to_port)
                        if fr_port_obj.buffer.shape != to_port_obj.buffer.shape:
                            sys.stderr.write("ERROR: Port dimension unmatched!\n")
                            return False
                        # Registering a connection
                        key = from_unit + ":" + to_unit
                        if key not in self.__connections_from_to:
                            self.__connections_from_to[key] = []
                        self.__connections_from_to[key].append((from_port, to_port))
                        if debug:
                            print(
                                "Creating a connection from " + from_port + " of " + from_unit + " to " + to_port +
                                " of " + to_unit + ".\n")
                    except KeyError:
                        sys.stderr.write(
                            "ERROR: adding a connection from " + from_unit + " to " + to_unit +
                            " on the same level but not from an output port to an input port!\n")
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
            if module_name in self.sub_modules:
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
                    # New ImplClass instance
                    self.unit_dic[module_name] = eval(implclass + '.__new__(' + implclass + ')')
                except (NameError, ValueError, SyntaxError):
                    v = implclass.rsplit(".", 1)
                    mod_name = v[0]
                    class_name = v[1]
                    try:
                        mod = __import__(mod_name, globals(), locals(), [class_name], 0)  # -1)
                        klass = getattr(mod, class_name)
                        self.unit_dic[module_name] = klass.__new__(klass)
                    except AttributeError:
                        sys.stderr.write("ERROR: Module " + module_name
                                         + " at the bottom not grounded as a Component!\n")
                        return_value = False
        return return_value

    def make_ports(self):
        for module_name, v in self.module_dictionary.items():
            try:
                ports = self.module_dictionary[module_name]['Ports']
                for port_name in ports:
                    full_port_name = module_name + "." + port_name
                    port_v = self.__ports[full_port_name]
                    self.__make_a_port(module_name, port_v['IO'], port_name, port_v['Shape'])
            except KeyError:
                sys.stderr.write("ERROR: cannot create a port for Component " + module_name + "!\n")
                return False
        return True

    def make_connections(self, modules):
        for submodule in modules:
            self.__set_aliases(submodule)
        for key in self.__connections_from_to.keys():
            module_names = key.split(':')
            for ports in self.__connections_from_to[key]:
                from_port, to_port = ports
                brica1.connect((self.unit_dic[module_names[0]], from_port), (self.unit_dic[module_names[1]], to_port))

    def __set_aliases(self, module_name):
        lower_modules = []
        lower_modules = self.__get_lower_modules(module_name, lower_modules)
        for sub_module in lower_modules:
            module_names = module_name + ":" + sub_module
            if module_names in self.__alias_in:
                for ports in self.__alias_in[module_names]:
                    from_port, to_port = ports
                    self.unit_dic[sub_module].alias_in_port(self.unit_dic[module_name], from_port, to_port)
            module_names = sub_module + ":" + module_name
            if module_names in self.__alias_out:
                for ports in self.__alias_out[module_names]:
                    from_port, to_port = ports  # from_port: sub / to_port: upper
                    self.unit_dic[sub_module].alias_out_port(self.unit_dic[module_name], to_port, from_port)
            self.__set_aliases(sub_module)

    def __get_lower_modules(self, module, lower_modules):
        if module in self.sub_modules:
            lower_modules = lower_modules + self.sub_modules[module]
            for submodule in self.sub_modules[module]:
                self.__get_lower_modules(submodule, lower_modules)
        return lower_modules

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
            for port in ports:  # BriCAL version 2
                if isinstance(port, dict):
                    port["Module"] = module["Name"].strip()
                    self.__set_a_port(port)

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
            if module_name in self.super_module:
                print("Super module '%s' of '%s' is replaced with '%s'." % (
                    self.super_module[module_name], module_name, supermodule))
            self.super_module[module_name] = supermodule
            if supermodule not in self.sub_modules:
                self.sub_modules[supermodule] = []
            self.sub_modules[supermodule].append(module_name)

        if "SubModules" in module:
            for submodule in module["SubModules"]:
                if submodule != "":
                    submodule = self.__prefix_base_name_space(submodule)
                    if module_name not in self.sub_modules:
                        self.sub_modules[module_name] = []
                    if submodule not in self.sub_modules[module_name]:
                        self.sub_modules[module_name].append(submodule)
                    self.super_module[submodule] = module_name

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
        while val in self.super_module:
            val = self.super_module[val]
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
        if "Comment" in connection:
            self.__comments["Connections." + connection_name] = connection["Comment"]

        if connection_name not in self.__connections:
            self.__connections[connection_name] = []
        self.__connections[connection_name].append((to_unit + "." + to_port, from_unit + "." + from_port))
        return True


class AgentBuilder:
    """
    The BriCA language interpreter.
    - creates a BriCA agent based on the file contents.
    """

    def __init__(self):
        self.INCONSISTENT = 1
        self.NOT_GROUNDED = 2
        self.unit_dic = None

    def create_agent(self, network):
        for module, super_module in network.super_module.items():
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
            if unit_key not in network.super_module:  # top level
                if isinstance(network.unit_dic[unit_key], brica1.Component):
                    agent.add_component(unit_key, network.unit_dic[unit_key])
                elif isinstance(network.unit_dic[unit_key], brica1.Module):
                    agent.add_submodule(unit_key, network.unit_dic[unit_key])
                sub_modules.append(unit_key)
                if debug:
                    print("Adding a module " + unit_key + " to a BriCA agent.")
        network.make_connections(sub_modules)
        self.unit_dic = network.unit_dic
        return agent

    def create_gym_agent(self, network, model, env):
        for module, super_module in network.super_module.items():
            if super_module in network.module_dictionary:
                if isinstance(network.unit_dic[module], brica1.Component):
                    network.unit_dic[super_module].add_component(module, network.unit_dic[module])
                elif isinstance(network.unit_dic[module], brica1.Module):
                    network.unit_dic[super_module].add_submodule(module, network.unit_dic[module])
                if debug:
                    print("Adding a module " + module + " to " + super_module + ".")

        sub_modules = []
        for unit_key in network.unit_dic.keys():
            if unit_key not in network.super_module:  # top level
                sub_modules.append(unit_key)

        # Main logic
        agent = brica1.brica_gym.GymAgent(model, env)
        network.make_connections(sub_modules)
        self.unit_dic = network.unit_dic
        return agent

    def get_modules(self):
        return self.unit_dic
