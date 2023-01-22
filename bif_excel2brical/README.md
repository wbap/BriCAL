# bif_excel2brical.py
Python script to convert a BIF file in the Excel format to the BriCAL format.

USE: python bif_excel2owl.py infile outfile  

Note: 
* The BIF file must contain a BriCA sheet with fromCircuit, fromPort, toCircuit, toPort, shape columns in this order.
* The script uses the Circuit sheet to obtain module hierarchy (hasParts), ImplClass (implementations), name and functionality.

As for the BIF Excel format, see [this document](https://docs.google.com/document/d/1kKGJeG_NjuWqp7uUYvcb_uBiahj7KS_rKfhxtS4LP3c/edit?usp=sharing).

