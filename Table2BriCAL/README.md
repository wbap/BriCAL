# BriCAL Generator

This program (table2brical.py) generates BriCAL JSON code from three text files:
* Connection Table:
A region-to-region matrix, where a cell represents a connection score.
The first line and the first column contains lists of IDs for regions.
* Region Table:
A list of properties of regions consisting of:
ID, abbreviation, full name, definition
* Inclusion Table (optional):
A list of (region ID, upper region ID) pairs

See [here](https://docs.google.com/document/d/1Hzx2IlM7AxhE4AlURHINNyWIyN0l_IUMTL1b1K_w5Tk/edit?usp=sharing) for the specification.
