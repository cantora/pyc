
SRCS		= $(wildcard ./*.c)
OBJS		= $(patsubst %.c, %.o, $(SRCS) )

.PHONY: all
all: $(OBJS)

.PHONY: clean
clean:
	rm -fv *.o