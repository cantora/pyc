
TMPDIR := /tmp/pyc

.PHONY: pkg
pkg: hw.zip

hw.zip: 
	rm -rf /tmp/pyc
	mkdir $(TMPDIR)
	cp pyc $(TMPDIR)/compile.py
	cp *.py $(TMPDIR)/
	cp runtime.c $(TMPDIR)/
	cp runtime.h $(TMPDIR)/
	cd $(TMPDIR) &&	zip hw.zip * 
	mv $(TMPDIR)/hw.zip ./

.PHONY: clean
clean:
	rm -fv hw.zip
	rm -fv output
	rm -fv ./clib/*.o
	rm -fv *.pyc
	for i in $$(find ./test/ -regex '.*\.\(\(expected\)\|\(out\)\|\(s\)\)'); do rm -v $$i; done

