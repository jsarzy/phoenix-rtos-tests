#
# Makefile for libphoenix tests
#
# Copyright 2020 Phoenix Systems
#
# %LICENSE%
#

$(PREFIX_PROG)test_fs: $(PREFIX_O)fs/test_fs.o
	$(LINK)

$(PREFIX_PROG)test_fcntl: $(PREFIX_O)fs/test_fcntl.o
	$(LINK)

all: $(addprefix $(PREFIX_PROG_STRIPPED), test_fs test_fcntl)
