#!/usr/bin/python2
import json
import os
import sys

from cpu import CPU
from migrator import Migrator
from process import Process

WORKLOAD_DIR = "workloads"
WORKLOAD_FILE_FMT = "./workloads/{}.json"
TRACE_FILE_FMT = "./traces/{}.trace.csv"

RUNNING = 0
SLEEPING = 1
SCHED_WAKEUP = "sched_wakeup"
TARGET_LATENCY = 11 * (10 ** 9)


def get_workload(workload):
    with open(WORKLOAD_FILE_FMT.format(workload), "r") as workload:
        return json.loads(workload.read())


def get_workloads():
    return [f.split(".")[0] for f in os.listdir(WORKLOAD_DIR)]


def list_workloads():
    for f in get_workloads():
        print "\t{}".format(f)


def main(argv):
    if len(argv) != 2:
        print "Usage: ./scheduler.py <WORKLOAD>"
        print
        print "Workloads"
        list_workloads()
        return

    workload = argv[1]
    if workload not in get_workloads():
        print "Unrecognized workload: {}".format(workload)
        return

    procs = []
    json_load = get_workload(workload)
    for proc in json_load['processes']:
        for i in range(proc['quantity']):
            trace = TRACE_FILE_FMT.format(proc['benchmark'])
            procs.append(Process(trace, "{}_{}".format(trace, i)))

    procs[0].print_state_list()
    num_cpus = json_load['cpus']

    migrator = Migrator()
    cpus = [CPU(procs[i::num_cpus], TARGET_LATENCY, i, migrator)
            for i in range(num_cpus)]
    for c in cpus:
        c.run()


if __name__ == '__main__':
    main(sys.argv)
