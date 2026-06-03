CC ?= cc
CFLAGS ?= -Wall -Wextra -O2 -g -fPIC
LDFLAGS ?= -shared
LDLIBS ?= -ldl -lXt -lX11

.PHONY: all clean

all: libxttap.so

libxttap.so: xttap.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

clean:
	rm -f libxttap.so *.o
