#!/usr/bin/python2
import json
import os
import sys

import matplotlib.pyplot as plt

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
PLOT_DIR = "./plots"


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

    sim_time = json_load['sim_time_millis'] * NANOS_PER_MILLISECOND
    runtime_plot = []
    for proc in json_load['processes']:
        for i in range(proc['quantity']):
            trace_name = proc['benchmark']
            trace = TRACE_FILE_FMT.format(trace_name)
            new_proc = Process(trace,
                               trace_name,
                               i, sim_time)
            procs.append(new_proc)
            if i == 0:
                runtime_plot.append(new_proc)

    procs[0].print_state_list()

    num_cpus = json_load['cpus']
    migrator = Migrator(json_load['max_latency_millis'])
    cpus = [CPU(procs[i::num_cpus],
                json_load['initial_latency_millis'] * NANOS_PER_MILLISECOND,
                i, migrator)
            for i in range(num_cpus)]

    time_run = 0
    rebalance_period = (json_load['rebalance_period_millis'] *
                        NANOS_PER_MILLISECOND)
    while any([c.has_unfinished_procs() for c in cpus]):
        for c in cpus:
            if c.has_unfinished_procs():
                c.run(rebalance_period)

        time_run += rebalance_period
        if time_run % (10 * rebalance_period) == 0:
            print time_run

        if json_load['dynamic']:
            migrator.rebalance()

        # for c in cpus:
        #     print "CPU {}: {}".format(c.number, c.scheduler.target_latency)
        #     for p in c.get_unfinished_procs():
        #         print "\t{}: {}".format(p.name,
        #                                 "r" if p == c.scheduler.curr_proc
        #                                 else "s")

    # make_runtime_plots(runtime_plot)
    report_raw_results(procs, json_load['dynamic'], migrator)

def report_raw_results(procs, dynamic, migrator):
    class Stats:
        def __init__(self, bench_name):
            self.bench_name = bench_name
            self.context_switches = 0
            self.proc_count = 0

        def update_stats(self, proc):
            assert proc.bench_name == self.bench_name
            self.proc_count += 1
            self.context_switches += proc.context_switches

        def normalize(self):
            self.context_switches /= self.proc_count

    if not os.path.exists(PLOT_DIR):
        os.mkdir(PLOT_DIR)

    stats_dict = {}
    for p in procs:
        stats_dict.setdefault(
            p.bench_name, Stats(p.bench_name)).update_stats(p)
        print ("{}\n***********************\n"
               "\tcontext switches {}\n"
               "\taverage runtime: {}\n"
               "\tload: {}\n"
               "\tfinished: {}\n").format(p.name,
                                          p.context_switches,
                                          p.average_runtime,
                                          p.get_load(),
                                          p.finished)

    for s in stats_dict.values():
        s.normalize()
        print "{}: {}".format(s.bench_name, s.context_switches)

    if dynamic:
        lats = migrator.historical_latencies
        print "Avg latency: {}".format(sum(lats) / len(lats))


def make_runtime_plots(procs):
    for p in procs:
        plt.title("Estimated Runtime: {}".format(p.name))
        plt.xlabel("Time (nanos)")
        plt.ylabel("Estimated Runtime (nanos)")
        plt.plot([x[0] for x in p.average_runtime_points],
                 [x[1] for x in p.average_runtime_points])
        plt.savefig('{}/runtime_{}.png'.format(PLOT_DIR, p.name))
        plt.clf()
        plt.close()


if __name__ == '__main__':
    main(sys.argv)
