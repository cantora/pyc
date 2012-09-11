
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
	mv $(TMPDIR)/hw.zpip ./

ply:
	wget 'http://www.dabeaz.com/ply/ply-3.4.tar.gz'
	tar -xzvf ./ply-3.4.tar.gz
	mv ply-3.4 ply

.PHONY: clean
clean:
	rm -fv hw.zip
	rm -fv output
	rm -fv ./clib/*.o
	rm -fv *.pyc
	for i in $$(find ./test/ -regex '.*\.\(\(expected\)\|\(out\)\|\(s\)\)'); do rm -v $$i; done
	if [ -d ./ply ]; then cd ./ply; rm -rv *; done

