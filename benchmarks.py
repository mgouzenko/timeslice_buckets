#!/usr/bin/python2
import sys

PHORONIX_TESTS = "/home/archie/.phoronix-test-suite/installed-tests"

BENCHMARKS = {
    "unpack_linux": "tar -xjf {root}/pts/linux-kernel-base-1.0.0/linux-2.6.32.tar.bz2 -C /tmp"
}

def get_benchmarks():
    benchmarks = {}
    for name, cmd in BENCHMARKS.iteritems():
        benchmarks[name] = cmd.format(root=PHORONIX_TESTS)
    return benchmarks
