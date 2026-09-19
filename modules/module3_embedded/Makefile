# EdgeSAR Module 3 Makefile
# Strict aerospace compiler flags conforming to DO-178C Level B and MISRA-C:2012

CC ?= gcc
CFLAGS ?= -Wall -Wextra -pedantic -std=c99 -Werror -Wstrict-prototypes -Wshadow -O2
INCLUDES = -Iinclude -Itests/unity

SRC = src/cfar_detector.c src/hal_sar_mock.c src/fft_mock.c
TEST_SRC = $(SRC) tests/unity/unity.c tests/test_cfar.c tests/test_hal.c tests/test_fft.c tests/test_runner.c
TEST_BIN = test_runner.exe

.PHONY: all test check clean

all: $(TEST_BIN)

$(TEST_BIN): $(TEST_SRC)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $(TEST_SRC) -lm

test: $(TEST_BIN)
	./$(TEST_BIN)

check:
	cppcheck --enable=all --error-exitcode=1 --inconclusive --std=c99 --suppress=unusedFunction --suppress=staticFunction --suppress=missingIncludeSystem --suppress=normalCheckLevelMaxBranches --suppress=checkersReport --suppress=unmatchedSuppression -I include src/

clean:
	rm -f $(TEST_BIN) *.o
