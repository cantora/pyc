
TMPDIR := /tmp/pyc
SRCS	= $(filter-out ./parsetab.py, $(wildcard ./*.py) )
P0TESTS	= $(wildcard ./p0tests/grader_tests/*.py) #\
			#$(filter-out %stack_test.py, $(wildcard ./p0tests/mytests/*.py) ) \
			#$(wildcard ./p0tests/student_tests/*.py)

P1TESTS	= $(filter-out %dict0.py %dict1.py %eq1.py %is0.py %list1.py %list2.py %list3.py %list4.py %list5.py %list6.py %list7.py, $(wildcard ./p1tests/grader_tests/*.py) )

.PHONY: pkg
pkg: hw.zip

hw.zip: ply $(SRCS) makefile
	rm -rf /tmp/pyc
	mkdir $(TMPDIR)
	cp pyc $(TMPDIR)/compile.py
	cp $(SRCS) $(TMPDIR)/
	cp clib/*.c $(TMPDIR)/
	cp clib/*.h $(TMPDIR)/
	cp -R ./ply $(TMPDIR)/ply
	cd $(TMPDIR) &&	zip -r hw.zip * 
	mv $(TMPDIR)/hw.zip ./

ply:
	wget 'http://www.dabeaz.com/ply/ply-3.4.tar.gz'
	tar -xzvf ./ply-3.4.tar.gz
	mv ply-3.4 ply
	rm ply-3.4.tar.gz

.PHONY: compile_test
compile_test:
	@for i in $(TESTS); do \
		./pyc $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
		echo "[x] $$(basename $$i)"; \
	done

.PHONY: p0tests
p0tests:
	@for i in $(P0TESTS); do \
		VERBOSE=0 ./test.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p1tests
p1tests:
	@for i in $(P1TESTS); do \
		VERBOSE=0 ./test.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: clean
clean:
	rm -fv hw.zip
	rm -fv output
	rm -fv ./clib/*.o
	rm -fv *.pyc
	for i in $$(find ./p0tests/ -regex '.*\.\(\(expected\)\|\(out\)\|\(s\)\)'); do rm -v $$i; done
	if [ -d ./ply ]; then rm -rv ./ply; fi

