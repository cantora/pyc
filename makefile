
TMPDIR := /tmp/pyc

.PHONY: pkg
pkg: hw.zip

hw.zip: ply
	rm -rf /tmp/pyc
	mkdir $(TMPDIR)
	cp pyc $(TMPDIR)/compile.py
	cp *.py $(TMPDIR)/
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

.PHONY: clean
clean:
	rm -fv hw.zip
	rm -fv output
	rm -fv ./clib/*.o
	rm -fv *.pyc
	for i in $$(find ./test/ -regex '.*\.\(\(expected\)\|\(out\)\|\(s\)\)'); do rm -v $$i; done
	if [ -d ./ply ]; then rm -rv ./ply; fi

