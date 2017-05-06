#!/usr/bin/python2
import sys

PHORONIX_TESTS = "/home/archie/.phoronix-test-suite/installed-tests"

BENCHMARKS = {
    # "unpack_linux": "tar -xjf {root}/pts/linux-kernel-base-1.0.0/linux-2.6.32.tar.bz2 -C /tmp",
    "unpack_linux": "bzcat {root}/pts/linux-kernel-base-1.0.0/linux-2.6.32.tar.bz2 > /tmp/linux",
    "test": "./a.out",
    "aiostress": "{root}/pts/aio-stress-1.1.1/aio-stress-bin -s 2g -r 64k -t 1 -o 2 \
{root}/pts/aio-stress-1.1.1/aio-test-file > /tmp/logfile 2>&1"
}

def get_benchmarks():
    benchmarks = {}
    for name, cmd in BENCHMARKS.iteritems():
        benchmarks[name] = cmd.format(root=PHORONIX_TESTS)
    return benchmarks
