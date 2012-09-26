
SRCS		= $(wildcard ./*.c)
OBJS		= $(patsubst %.c, %.o, $(SRCS) )

.PHONY: all
all: $(OBJS)

%.o: %.c
	gcc -m32 -c $<

.PHONY: clean
clean:
	rm -fv *.o