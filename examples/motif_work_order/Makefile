CC ?= cc
CFLAGS ?= -Wall -Wextra -O2 -g
LDLIBS ?= -lXm -lXt -lX11

TARGET := motif-work-order
SOURCES := motif_work_order.c

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CC) $(CFLAGS) -o $@ $(SOURCES) $(LDLIBS)

clean:
	rm -f $(TARGET) *.o
