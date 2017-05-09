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

NANOS_PER_MILLISECOND = (10 ** 6)
TARGET_LATENCY = 10 * NANOS_PER_MILLISECOND

# Rebalance every 30 milliseconds. This is 5 latency cyles for linux.
REBALANCE_INTERVAL = 30 * NANOS_PER_MILLISECOND
MAX_TIME = 5000 * NANOS_PER_MILLISECOND


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
            trace_name = proc['benchmark']
            trace = TRACE_FILE_FMT.format(trace_name)
            procs.append(Process(trace,
                                 "{}_{}".format(trace_name, i),
                                 MAX_TIME))

    procs[0].print_state_list()
    num_cpus = json_load['cpus']

    migrator = Migrator()
    cpus = [CPU(procs[i::num_cpus], TARGET_LATENCY, i, migrator)
            for i in range(num_cpus)]

    time_run = 0
    while any([c.has_running_procs() for c in cpus]):
        for c in cpus:
            if c.has_running_procs():
                c.run(REBALANCE_INTERVAL)

        time_run += REBALANCE_INTERVAL
        if time_run % (50 * REBALANCE_INTERVAL):
            print time_run

        migrator.rebalance()

    for c in cpus:
        c.report_results()


if __name__ == '__main__':
    main(sys.argv)
