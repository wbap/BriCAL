# BriCAL
BriCA Language Interpreter for BriCA Core Version 1

The BriCA Language is a DSL (Domain Specific Language) for describing the structure of cognitive architecture mimicking the brain.  It describes networks consisting of modules having ports and connections between them.  Modules can be nested.  Currently port values are numeric vectors.

Language specification is found [here](https://docs.google.com/document/d/1A8WCKFynadMEyRpl5c5o0Pdh2hoY9WHOM0jdSA-yiIE/edit)

The interpreter reads BriCA language files (currently language files are in JSON) and checks network consistency (NetworkBuilder class).  It also build BriCA agents based on the network to make it executable (AgentBuilder class).

* [JSON format](https://drive.google.com/open?id=1J2aZBhpqTZ2z1BbqObvsh2YeMihFKn1TUW5pTjDBjfQ)
* [Language Interpreter Specification](https://drive.google.com/open?id=1D5lO1mC0B1BBAGiCUug6LtG8M8IFvYKZRopBUBj2zpA)
* [BriCA Core](http://wbap.github.io/BriCA1/)

## Example use case:
Clone brica1 and brical from GitHub.

Add brica related paths to PYTHONPATH:

	export PYTHONPATH=[YOUR GIT DIRECTORY]/brical:[YOUR GIT DIRECTORY]/brica1:$PYTHONPATH

Launch python (3.*):


	$ python


Import libraries:

	>>> import numpy as np
	>>> import brical
	>>> import brica1    

Instantiate brical.NetworkBuilder.

	>>> nb=brical.NetworkBuilder()

Load JSON files:

In this example, you load six files from 'test/n001' directory.

	>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/01InputComponent.json")
	>>> nb.load_file(f)
	True
	>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/02MainComponent.json")
	>>> nb.load_file(f)
	True
	>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/03OutputComponent.json")
	>>> nb.load_file(f)
	True
	>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/04SuperInput.json")
	>>> nb.load_file(f)
	True
	>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/05SuperMain.json")
	>>> nb.load_file(f)
	True
	>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/06SuperOutput.json")
	>>> nb.load_file(f)
	True

Check network consistency:

	>>> nb.check_consistency()
	True

Procedures before running the BriCA network with AgentBuilder class:

	>>> network = nb.get_network()
	>>> agent_builder = brical.AgentBuilder()
	>>> agent = agent_builder.create_agent(nb)
	>>> scheduler = brica1.VirtualTimeSyncScheduler(agent)

BriCA modules are accessed via the module dictionary obtained with agent_builder.get_modules():

	>>> modules = agent_builder.get_modules()

Setting non-zero values to the input module:

	>>> v = np.array([1, 2, 3], dtype=np.int16)
	>>> modules["BriCA1.InputModule"].set_state("InputModulePort", v)

Setting a map for PipeComponent (see BriCA1 tutorial for explanation):

	>>> modules["BriCA1.MainModule"].set_map("Port1", "Port2")

Now run the network step by step and see if values are transmitted to the ports:

	>>> scheduler.step()
	1
	>>> modules["BriCA1.InputModule"].get_out_port("InputModulePort").buffer
	array([1, 2, 3], dtype=int16)
	>>> modules["BriCA1.MainModule"].get_out_port("Port2").buffer
	array([0, 0, 0], dtype=int16)
	>>> scheduler.step()
	2
	>>> modules["BriCA1.MainModule"].get_out_port("Port2").buffer
	array([1, 2, 3], dtype=int16)
	>>> scheduler.step()
	3
	>>> modules["BriCA1.OutputModule"].get_in_port("OutputModulePort").buffer
	array([1, 2, 3], dtype=int16)

## Support:
If you have any question, please send us message on Google Group:  
https://groups.google.com/d/forum/wbai-dev
