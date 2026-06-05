CC ?= cc
CFLAGS ?= -Wall -Wextra -O2 -g -fPIC
LDFLAGS ?= -shared
LDLIBS ?= -ldl -lXt -lX11

.PHONY: all test clean

all: libxttap.so

libxttap.so: xttap.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

test: xttap-self-test
	./xttap-self-test

xttap-self-test: xttap.c
	$(CC) $(CFLAGS) -DMOTIF_TAP_SELF_TEST -o $@ $< $(LDLIBS)

clean:
	rm -f libxttap.so xttap-self-test *.o
