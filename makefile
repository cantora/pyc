
TMPDIR := /tmp/pyc
SRCS	= $(filter-out ./parsetab.py, $(wildcard ./*.py) )
TESTS	= $(wildcard ./grader_tests/*.py) \
			$(filter-out %stack_test.py, $(wildcard ./test/*.py) ) \
			$(wildcard ./student_tests/*.py)
			

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

.PHONY: test
test:
	@for i in $(TESTS); do \
		VERBOSE=0 ./test.sh $$i; \
		if [ $$? -ne 0 ]; then \
			echo "FAILED: $$(basename $$i)"; \
			break; \
		fi; \
		echo "[x] $$(basename $$i)"; \
	done

.PHONY: clean
clean:
	rm -fv hw.zip
	rm -fv output
	rm -fv ./clib/*.o
	rm -fv *.pyc
	for i in $$(find ./test/ -regex '.*\.\(\(expected\)\|\(out\)\|\(s\)\)'); do rm -v $$i; done
	if [ -d ./ply ]; then rm -rv ./ply; fi

