#!/usr/bin/python2
import os
import sys


class Benchmark(object):
    PHORONIX_TESTS = "~/.phoronix-test-suite/installed-tests"

    def __init__(self, benchmark_cmd, preparation_cmd=None):
        self.preparation_cmd = (
            preparation_cmd.format(root=self.PHORONIX_TESTS, uid=os.getuid()) if
            preparation_cmd is not None else None)
        self.benchmark_cmd = benchmark_cmd.format(root=self.PHORONIX_TESTS,
                                                  uid=os.getuid())

BENCHMARKS = {
    "unpack_linux": Benchmark("tar -xJf ./test_materials/linux-4.11.tar.xz "
                              " > /tmp/{uid}/linux"),

    "test": Benchmark("/tmp/{uid}/a.out",
                      preparation_cmd="gcc ./test_materials/test.c -o /tmp/{uid}/a.out"),

    "zip": Benchmark(
        "zip --password hello /tmp/{uid}/random_bytes.zip /tmp/{uid}/random_bytes",
        preparation_cmd=("ls /tmp/{uid}/random_bytes || dd if=/dev/urandom bs=4096 count=100000 "
                         "of=/tmp/{uid}/random_bytes")),

    "md5": Benchmark(
        "md5sum /tmp/{uid}/md5bytes",
        preparation_cmd=("ls /tmp/{uid}/md5bytes || dd if=/dev/urandom bs=4096 count=1000000 "
                         "of=/tmp/{uid}/md5bytes ")),

    "dd": Benchmark((
        "dd if=/dev/urandom bs=4096 count=10000 of=/tmp/{uid}/dd_test")),

    "aiostress": Benchmark(
        "{root}/pts/aio-stress-1.1.1/aio-stress-bin -s 2g -r 64k -t 1 -o 2 "
        "{root}/pts/aio-stress-1.1.1/aio-test-file > /tmp/logfile 2>&1")
}
