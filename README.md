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
<pre><code>export PYTHONPATH=[YOUR GIT DIRECTORY]/brical:[YOUR GIT DIRECTORY]/brica1:$PYTHONPATH
</code></pre>
Launch python (2.7):

`
$ python
`

Import libraries:
<pre><code>>>> import numpy as np
>>> import brical
>>> import brica1    
</code></pre>
Instantiate brical.NetworkBuilder.
<pre><code>>>> nb=brical.NetworkBuilder()
</code></pre>
Load JSON files:

In this example, you load six files from 'test/n001' directory.
<pre><code>>>> f = open("[YOUR GIT DIRECTORY]/brical/test/n001/01InputComponent.json")
>>> nb.load_file(f)
True
>>> f = open("[YOUR GIT DIRECTORY]/brical20160208/brical/test/n001/02MainComponent.json")
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
</code></pre>
Check network consistency:
<pre><code>>>> nb.check_consistency()
True
</code></pre>
Procedures before running the BriCA network with AgentBuilder class:
<pre><code>>>> network = nb.get_network()
>>> scheduler = brica1.VirtualTimeSyncScheduler()
>>> agent_builder = brical.AgentBuilder()
>>> agent = agent_builder.create_agent(scheduler, nb)
</code></pre>
BriCA modules are accessed via the module dictionary obtained with agent_builder.get_modules():
<pre><code>>>> modules = agent_builder.get_modules()
</code></pre>
Setting non-zero values to the input module:
<pre><code>>>> v = np.array([1, 2, 3], dtype=np.int16)
>>> modules["BriCA1.InputModule"].get_component("BriCA1.InputModule").set_state("InputModulePort", v)
</code></pre>
Setting a map for PipeComponent (see BriCA1 tutorial for explanation):
<pre><code>>>> modules["BriCA1.MainModule"].get_component("BriCA1.MainModule").set_map("Port1", "Port2")
</code></pre>
Now run the network step by step and see if values are transmitted to the ports:
<pre><code>>>> agent.step()
1.0
>>> modules["BriCA1.InputModule"].get_out_port("InputModulePort").buffer
array([1, 2, 3], dtype=int16)
>>> modules["BriCA1.MainModule"].get_out_port("Port2").buffer
array([0, 0, 0], dtype=int16)
>>> agent.step()
2.0
>>> modules["BriCA1.MainModule"].get_out_port("Port2").buffer
array([1, 2, 3], dtype=int16)
>>> agent.step()
3.0
>>> modules["BriCA1.OutputModule"].get_in_port("OutputModulePort").buffer
array([1, 2, 3], dtype=int16)
</code></pre>