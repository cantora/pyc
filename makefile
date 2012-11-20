
TMPDIR := /tmp/pyc
SRCS	= $(filter-out ./parsetab.py, $(wildcard ./*.py) )
P0TESTS	= $(wildcard ./p0tests/grader_tests/*.py) #\
#$(filter-out %stack_test.py, $(wildcard ./p0tests/mytests/*.py) ) \
#$(wildcard ./p0tests/student_tests/*.py)

P1TESTS	= $(wildcard ./p1tests/grader_tests/*.py)
P2TESTS	= $(wildcard ./p2tests/grader_tests/*.py)
P3TESTS	= $(wildcard ./p3tests/grader_tests/*.py) $(wildcard ./p3tests/my_tests/*.py)

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

.PHONY: tests
tests: p0tests p1tests p2tests p3tests

.PHONY: ir-tests
ir-tests: p0-irtests p1-irtests p2-irtests p3-irtests

.PHONY: ir-line-tests
ir-line-tests: p0-ir-linetests p1-ir-linetests p2-ir-linetests p3-ir-linetests

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

.PHONY: p2tests
p2tests:
	@for i in $(P2TESTS); do \
		VERBOSE=0 ./test.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p3tests
p3tests:
	@for i in $(P3TESTS); do \
		VERBOSE=0 ./test.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p0-irtests
p0-irtests:
	@for i in $(P0TESTS); do \
		VERBOSE=0 ./test-ir.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p1-irtests
p1-irtests:
	@for i in $(P1TESTS); do \
		VERBOSE=0 ./test-ir.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p2-irtests
p2-irtests:
	@for i in $(P2TESTS); do \
		VERBOSE=0 ./test-ir.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p3-irtests
p3-irtests:
	@for i in $(P3TESTS); do \
		VERBOSE=0 ./test-ir.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p0-ir-linetests
p0-ir-linetests:
	@for i in $(P0TESTS); do \
		VERBOSE=0 ./test-ir-line.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p1-ir-linetests
p1-ir-linetests:
	@for i in $(P1TESTS); do \
		VERBOSE=0 ./test-ir-line.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p2-ir-linetests
p2-ir-linetests:
	@for i in $(P2TESTS); do \
		VERBOSE=0 ./test-ir-line.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
	done

.PHONY: p3-ir-linetests
p3-ir-linetests:
	@for i in $(P3TESTS); do \
		VERBOSE=0 ./test-ir-line.sh $$i; \
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

