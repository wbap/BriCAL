import xml.etree.ElementTree as et
import rdflib
import argparse
import json


def get_label(graph, uri):
    q = """
    SELECT DISTINCT ?a ?aname
    WHERE {
        <""" + uri + """> rdfs:label ?aname.
    }"""
    qres2 = graph.query(q)
    for row2 in qres2:
        return str(row2.aname)
    return ""


def get_function(graph, uri):
    q = """
    PREFIX bifd: <https://wba-initiative.org/bifd/>
    SELECT DISTINCT ?a ?aname
    WHERE {
        <""" + uri + """> bifd:functionality ?aname.
    }"""
    qres2 = graph.query(q)
    for row2 in qres2:
        return str(row2.aname)
    return ""


def get_submodules(g, uri):
    q = """
    SELECT DISTINCT ?m
    WHERE {
        <""" + uri + """> rdfs:subClassOf ?b.
        ?b rdf:type owl:Restriction.
        ?b owl:onProperty <https://wba-initiative.org/bifd/hasPart>.
        ?b owl:someValuesFrom ?m.
    }"""
    qres = g.query(q)
    modules = []
    for row in qres:
        m = str(row.m)
        modules.append(m[m.rfind("/")+1:])
    return modules


def get_name_from_uri(uri):
    return uri[uri.rfind('/', 0, -2) + 1:-1] if uri[-1] == '/' else uri[uri.rfind('/') + 1]


def get_base_from_uri(uri):
    items = uri.split('/')
    return items[-2] if uri[-3] == '/' else items[-2]


def upper_p(module1, module2, modules):
    if 'SubModules' in modules[module1]:
        submodules = modules[module1]['SubModules']
        if module2 in submodules:
            return True
        else:
            for submodule in submodules:
                if upper_p(submodule, module2, modules):
                    return True
    else:
        return False
    return False


# Collecting Connections
def define_connections(modules, module_uris, g):
    connections = {}
    base_uri = ""
    q = """
    SELECT DISTINCT ?a ?aname ?from_uri ?to_uri
    WHERE {
        ?a rdfs:label ?aname .
        ?a rdfs:subClassOf bifd:Connection.
        ?a rdfs:subClassOf ?b.
        ?b rdf:type owl:Restriction.
        ?b owl:onProperty <https://wba-initiative.org/bifd/inputCircuit>.
        ?b owl:someValuesFrom ?from_uri.
        ?a rdfs:subClassOf ?c.
        ?c rdf:type owl:Restriction.
        ?c owl:onProperty <https://wba-initiative.org/bifd/outputCircuit>.
        ?c owl:someValuesFrom ?to_uri.
    }"""
    qres = g.query(q)
    for row in qres:
        connection = str(row.aname)
        if base_uri == "":
            uri = str(row.a)
            base_uri = uri[:uri.rfind("/")+1]
        mds = connection.split("-")
        from_module = mds[0]
        to_module = mds[1]
        if from_module not in modules:
            modules[from_module] = {"Name": from_module, "Ports": []}
            module_uris[from_module] = row.from_uri
        if to_module not in modules:
            modules[to_module] = {"Name": to_module, "Ports": []}
            module_uris[to_module] = row.to_uri
        connections[connection] = {"Name": connection, "FromModule": from_module, "FromPort": connection,
                                   "ToModule": to_module, "ToPort": connection}
    return connections, base_uri


# Collecting Modules
def define_modules(modules, module_uris, graphs, g, base_uri):
    for v in modules.values():
        name = v["Name"]
        uri = str(module_uris[name])
        v["Comment"] = get_base_from_uri(uri) + ":" + get_label(graphs[get_base_from_uri(uri)], uri) + ": " + \
                       get_function(graphs[get_base_from_uri(uri)], uri)
        submodules = get_submodules(g, base_uri + name)
        if len(submodules) > 0:
            v["SubModules"] = submodules
        else:
            v["ImplClass"] = ""
    return modules


# Defining Ports
def define_ports(connections, modules):
    ports = []
    for connection in connections:
        v = connections[connection]
        from_module = v["FromModule"]
        to_module = v["ToModule"]
        if upper_p(from_module, to_module, modules):
            connection_from = "Input"
            connection_to = "Input"
        elif upper_p(to_module, from_module, modules):
            connection_from = "Output"
            connection_to = "Output"
        else:
            connection_from = "Output"
            connection_to = "Input"
        ports.append({"Name": connection, "Module": from_module, "Type": connection_from, "Shape": [1]})
        ports.append({"Name": connection, "Module": to_module, "Type": connection_to, "Shape": [1]})
        modules[from_module]["Ports"].append(connection)
        modules[to_module]["Ports"].append(connection)
    return ports


def main():
    # Main Program
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="input file", type=str)
    parser.add_argument("--output", help="output file", type=str)
    parser.add_argument("--bifd", help="bifd.owl", type=str)
    parser.add_argument("--external_ontologies", nargs='*', help="URIs", type=str)
    args = parser.parse_args()

    URI_TMP = 'https://wba-initiative.org/noprefix/'
    BASE = '{http://www.w3.org/XML/1998/namespace}base'

    # Get BIFD
    g_bifd = rdflib.Graph()
    g_bifd.parse(args.bifd, publicID=URI_TMP, format="xml")

    # Get Base and Graph
    tree = et.parse(args.input)
    base = get_name_from_uri(tree.getroot().get(BASE))

    g = rdflib.Graph()
    g.parse(args.input, publicID=URI_TMP, format="xml")

    graphs = {base: g}

    # Get External Ontologies
    if args.external_ontologies is not None:
        for eo in args.external_ontologies:
            tree = et.parse(eo)
            eo_base = get_name_from_uri(tree.getroot().get(BASE))
            eo_g = rdflib.Graph()
            eo_g.parse(eo, publicID=URI_TMP, format="xml")
            graphs[eo_base] = eo_g

    modules = {}
    module_uris = {}
    connections, base_uri = define_connections(modules, module_uris, g)
    modules = define_modules(modules, module_uris, graphs, g, base_uri)
    ports = define_ports(connections, modules)

    module_array = []
    for v in modules.values():
        module_array.append(v)

    output = {"Header": {"Type": "A", "Name": base, "Base": base}, "Modules": module_array, "Ports": ports}
    connection_array = []
    for v in connections.values():
        connection_array.append(v)
    output["Connections"] = connection_array

    fp = open(args.output, 'w')
    json.dump(output, fp, indent=1)
    fp.close()


if __name__ == '__main__':
    main()
