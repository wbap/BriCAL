#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import brical

import_modules = [
    'import gym',
    'import numpy as np',
    'import sys',
    'import argparse',
    'import json',
    'import brica1.brica_gym',
    'import brical'
]

main_code1 = [
    'def main():',
    '    parser = argparse.ArgumentParser(description=\'$PROJECT_DESCRIPTION$\')',
    '    parser.add_argument(\'--dump\', help=\'dump file path\')',
    '    parser.add_argument(\'--episode_count\', type=int, default=1, metavar=\'N\',',
    '                        help=\'Number of training episodes (default: 1)\')',
    '    parser.add_argument(\'--max_steps\', type=int, default=30, metavar=\'N\',',
    '                        help=\'Max steps in an episode (default: 20)\')',
    '    parser.add_argument(\'--config\', type=str, default=\'$PROJECT_NAME$.json\', metavar=\'N\',',
    '                        help=\'Model configuration (default: $PROJECT_NAME$.json\')',
    '    parser.add_argument(\'--brical\', type=str, default=\'$PROJECT_NAME$.brical.json\', metavar=\'N\',',
    '                        help=\'a BriCAL json file\')',
    '    args = parser.parse_args()',
    '',
    '    with open(args.config) as config_file:',
    '        config = json.load(config_file)',
    '',
    '    nb = brical.NetworkBuilder()',
    '    f = open(args.brical)',
    '    nb.load_file(f)',
    '    if not nb.check_consistency():',
    '        sys.stderr.write("ERROR: " + args.brical + " is not consistent!")',
    '        exit(-1)',
    '',
    '    if not nb.check_grounding():',
    '        sys.stderr.write("ERROR: " + args.brical + " is not grounded!")',
    '        exit(-1)',
    '',
    '    train = {"episode_count": args.episode_count, "max_steps": args.max_steps}',
    '    config[\'train\'] = train',
    '',
    '    env = gym.make(config[\'env\'][\'name\'], config=config[\'env\'])',
    ''
]

main_code2 = [
    '    nb.make_ports()',
    '',
    '    agent_builder = brical.AgentBuilder()',
    '    model = nb.unit_dic[\'$TOP_MODULE$\']',
    '    agent = agent_builder.create_gym_agent(nb, model, env)',
    '    scheduler = brica1.VirtualTimeSyncScheduler(agent)',
    '',
    '    for i in range(train["episode_count"]):',
    '        last_token = 0',
    '        for j in range(train["max_steps"]):',
    '            scheduler.step()',
    '            current_token = agent.get_out_port(\'token_out\').buffer[0]',
    '            if last_token + 1 == current_token:',
    '                last_token = current_token',
    '                # TODO: WRITE END OF ENV CYCLE CODE HERE!!',
    '            if agent.env.done:',
    '                break',
    '        agent.env.flush = True'
]

main_code3 = [
    '        # TODO: WRITE END OF EPISODE CODE (component reset etc.) HERE!!',
    '        agent.env.reset()',
    '        agent.env.done = False',
    ''
]

main_call = [
    'if __name__ == \'__main__\':',
    '    main()',
]


def write_classes(name, ports, comment, wf):
    wf.write('# ' + comment + '\n')
    wf.write('class ' + name + '(brica1.brica_gym.Component):\n')
    wf.write('    def __init__(self, config):\n')
    wf.write('        super().__init__()\n')
    for port in ports:
        if port['Type'] == 'Input':
            wf.write('        self.make_in_port(\'' + port['Name'] + '\', ' + str(port['Shape'][0]) + ')\n')
    for port in ports:
        if port['Type'] == 'Output':
            wf.write('        self.make_out_port(\'' + port['Name'] + '\', ' + str(port['Shape'][0]) + ')\n')
    wf.write('\n')
    wf.write('    def fire(self):\n')
    wf.write('        pass  # TODO: WRITE CLASS LOGIC HERE!!\n')
    wf.write('\n')
    wf.write('    def reset(self):\n')
    wf.write('        self.token = 0\n')
    wf.write('        self.inputs[\'token_in\'] = np.array([0])\n')
    wf.write('        self.results[\'token_out\'] = np.array([0])\n')
    wf.write('        self.get_in_port(\'token_in\').buffer = self.inputs[\'token_in\']\n')
    wf.write('        self.get_out_port(\'token_out\').buffer = self.results[\'token_out\']\n')
    for i in range(2):
        wf.write('\n')


def main():
    if len(sys.argv) <= 2:
        print("USE: python brical2py.py infile outfile")
        exit()

    infilePath = sys.argv[1]
    outfilePath = sys.argv[2]

    nb = brical.NetworkBuilder()
    f = open(infilePath)
    nb.load_file(f)
    if not nb.check_consistency():
        sys.stderr.write("ERROR: " + infilePath + " is not consistent!\n")
        exit(-1)

    nw = nb.get_network()

    wf = open(outfilePath, 'w')

    hdr_comments = 'Header.' + nb.base_name_space

    wf.write('# !/usr/bin/env python\n')
    wf.write('# -*- coding: utf-8 -*-\n')
    wf.write('# ' + hdr_comments + '\n')

    # module imports
    for item in import_modules:
        wf.write(item + '\n')

    for i in range(2):
        wf.write('\n')

    top_level = []
    for unit_key in nb.unit_dic.keys():
        if unit_key not in nb.super_module:  # top level
            top_level.append(unit_key)

    for key, value in nb.module_dictionary.items():
        if 'ImplClass' in value and value['ImplClass'] != '':
            write_classes(key.replace(nb.base_name_space + '.', ''),
                          value['Ports'], nw['Comments']['Modules.' + key], wf)

    if len(top_level) == 1:
        top_module = top_level[0]
    else:
        top_module = '$TOP_MODULE$'

    components = []
    for key, value in nb.module_dictionary.items():
        if 'ImplClass' in value and value['ImplClass'] != '':
            components.append(key)

    # main code
    for item in main_code1:
        itm = item.replace('$PROJECT_DESCRIPTION$', nw['Comments'][hdr_comments]).\
            replace('$PROJECT_NAME$', nb.base_name_space). \
            replace('$TOP_MODULE$', top_module)
        wf.write(itm + '\n')

    for component in components:
        wf.write('    nb.unit_dic[\'' + component + '\'].__init__(config)\n')

    for item in main_code2:
        itm = item.replace('$PROJECT_DESCRIPTION$', nw['Comments'][hdr_comments]).\
            replace('$PROJECT_NAME$', nb.base_name_space). \
            replace('$TOP_MODULE$', top_module)
        wf.write(itm + '\n')

    for component in components:
        wf.write('        nb.unit_dic[\'' + component + '\'].reset()\n')

    for item in main_code3:
        wf.write(item + '\n')

    # closing
    for component in components:
        wf.write('    # nb.unit_dic[\'' + component + '\'].close()\n')
    wf.write('    print("Close")\n')
    wf.write('    env.close()\n')

    for i in range(2):
        wf.write('\n')

    # calling __main__
    for item in main_call:
        wf.write(item + '\n')

    wf.close()


if __name__ == '__main__':
    main()
