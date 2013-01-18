##### pyc

a python -> x86 compiler written in python (with a supporting runtime c library)

##### intro
pyc was implemented following the design by CU EE/CS instructor Jeremy Siek 
(detailed in doc/notes.pdf) during my enrollment in Siek's compiler design class at CU. 
the runtime c library and pN/grader_tests/* regression tests were provided by Siek.

the pyc_dbg*.py and pyc-dbg files implement debugging functionality for binaries compiled
with pyc/gcc using the python GDB extensions, the pyelftools package, and the distorm package.

##### building
to compile c library on 64 bit:  
	*get the proper headers/libraries (on ubuntu: sudo apt-get install gcc-multilib libc6-i386 libc6-dev-i386)

python packages needed for debugging:  
	*pyelftools: 	pip install pyelftools
	*distorm: 		pip install distorm3

