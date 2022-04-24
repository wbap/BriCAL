#!/usr/bin/env python

import sys
import argparse
import json

import numpy as np
import brica1
import brical


def main():
    parser = argparse.ArgumentParser(description='BriCAL use case n001')
    parser.add_argument('--brical',  type=str, default='n001.brical.json', metavar='N',
                        help='a BriCAL json file')
    args = parser.parse_args()

    # Instantiate brical.NetworkBuilder:
    nb = brical.NetworkBuilder()
    f = open(args.brical)
    nb.load_file(f)

    # Check network consistency:
    if not nb.check_consistency():
        sys.stderr.write("ERROR: " + args.brical + " is not consistent!\n")
        exit(-1)

    # Check component grounding:
    if not nb.check_grounding():
        sys.stderr.write("ERROR: " + args.brical + " is not grounded!\n")
        exit(-1)

    # Initializing components (according to the component specs):
    nb.unit_dic['n001.InputComponent'].__init__()
    nb.unit_dic['n001.MainComponent'].__init__()
    nb.unit_dic['n001.OutputComponent'].__init__()

    # Creating ports:
    nb.make_ports()

    # Procedures before running the BriCA network with AgentBuilder class:
    agent_builder = brical.AgentBuilder()
    agent = agent_builder.create_agent(nb)
    scheduler = brica1.VirtualTimeSyncScheduler(agent)

    # BriCA modules are accessed via the module dictionary obtained with agent_builder.get_modules():
    modules = agent_builder.get_modules()

    # Setting non-zero values to the input module:
    v = np.array([1, 2, 3], dtype=np.int16)
    modules["n001.InputComponent"].set_state("InputComponentPort", v)

    # Setting a map for PipeComponent (see BriCA1 tutorial for explanation):
    modules["n001.MainComponent"].set_map("Port1", "Port2")

    # Now run the network step by step and see if values are transmitted to the ports:
    print(scheduler.step())
    sys.stdout.write("InputComponentPort: {0}\n".
                     format(modules["n001.InputComponent"].get_out_port("InputComponentPort").buffer))
    sys.stdout.write("SuperMainModule.PortS2: {0}\n".
                     format(modules["n001.SuperMainModule"].get_out_port("PortS2").buffer))
    sys.stdout.write("OutputComponentPort:: {0}\n".
                     format(modules["n001.OutputComponent"].get_in_port("OutputComponentPort").buffer))

    print(scheduler.step())
    sys.stdout.write("SuperMainModule.PortS2: {0}\n".
                     format(modules["n001.SuperMainModule"].get_out_port("PortS2").buffer))
    sys.stdout.write("OutputComponentPort:: {0}\n".
                     format(modules["n001.OutputComponent"].get_in_port("OutputComponentPort").buffer))

    print(scheduler.step())
    sys.stdout.write("OutputComponentPort:: {0}\n".
                     format(modules["n001.OutputComponent"].get_in_port("OutputComponentPort").buffer))


if __name__ == '__main__':
    main()
