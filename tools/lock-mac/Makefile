CC = clang
LIBS =
INCLUDE =
FRAMEWORKS = -framework login
CFLAGS = -Wall -Werror
LFLAGS = -F /System/Library/PrivateFrameworks

SRCS = LockMac.c
OBJS = $(SRCS:.c=.o)
MAIN = lock-mac

$(MAIN): $(OBJS)
	$(CC) $(INCLUDE) $(CFLAGS) $(LIBS) $(FRAMEWORKS) $(LFLAGS) -o $(MAIN) $(OBJS)

.c.o:
	$(CC) $(CLAGS) $(INCLUDES) -c $< -o $@

run: $(MAIN)
	./$(MAIN)

clean:
	rm -f *.o $(MAIN)
