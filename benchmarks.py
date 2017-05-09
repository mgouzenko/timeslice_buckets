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
    # "unpack_linux": "tar -xjf {root}/pts/linux-kernel-base-1.0.0/linux-2.6.32.tar.bz2 -C /tmp",
    # "unpack_linux": Benchmark("tar -xjf {root}/pts/linux-kernel-base-1.0.0/"
    #                           "linux-2.6.32.tar.bz2 > /tmp/{uid}/linux"),
    "unpack_linux": Benchmark("tar -xJf ./test_materials/linux-4.11.tar.xz "
                              " > /tmp/{uid}/linux"),

    "test": Benchmark("/tmp/{uid}/a.out",
                      preparation_cmd="gcc ./test.c -o /tmp/{uid}/a.out"),

    "wget": Benchmark("wget https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-4.11.tar.xz > /tmp/{uid}/kernel"),

    "convert": Benchmark("convert ./test_materials/img.jpg -resize 200x200 ./test_materials/img-reduced.jpg"),

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

    "stream": Benchmark(
        "{root}/pts/stream-1.3.1/stream-bin > /tmp/{uid}/logfile 2>&1",
        preparation_cmd="export OMP_NUM_THREADS=1"),

    "aiostress": Benchmark(
        "{root}/pts/aio-stress-1.1.1/aio-stress-bin -s 2g -r 64k -t 1 -o 2 "
        "{root}/pts/aio-stress-1.1.1/aio-test-file > /tmp/logfile 2>&1")
}
