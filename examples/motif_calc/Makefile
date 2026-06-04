CC ?= cc
CFLAGS ?= -Wall -Wextra -O2 -g
LDLIBS ?= -lXm -lXt -lX11 -lm

TARGET := motif-calc
SOURCES := motif_calc.c

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CC) $(CFLAGS) -o $@ $(SOURCES) $(LDLIBS)

clean:
	rm -f $(TARGET) *.o
