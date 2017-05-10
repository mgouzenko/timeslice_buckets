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
    """Load a JSON configuration of the workload."""
    with open(WORKLOAD_FILE_FMT.format(workload), "r") as workload:
        return json.loads(workload.read())


def get_workloads():
    """Return a listing of all workloads."""
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

    json_load = get_workload(workload)

    # How much passing time we want to simulate. For example, if this is 5000,
    # we want to simulate 5 seconds worth of the trace.
    sim_time = json_load['sim_time_millis'] * NANOS_PER_MILLISECOND

    # List of process objects representing each workload; these will be split
    # between CPUs.
    procs = []

    # A subset of the procs list (defined above). This subset is used to plot
    # moving average runtime VS time.
    sample_procs = []

    for proc in json_load['processes']:
        for i in range(proc['quantity']):
            trace_name = proc['benchmark']
            trace_file = TRACE_FILE_FMT.format(trace_name)
            new_proc = Process(trace_file,
                               trace_name,
                               i, sim_time)
            procs.append(new_proc)
            if i == 0:
                sample_procs.append(new_proc)

    num_cpus = json_load['cpus']

    cpus = [
        CPU(
            # The processes the CPU is in charge of
            procs[i::num_cpus],

            # The initial CFS target latency, before the time packing algorithm
            # kicks in.
            json_load['initial_latency_millis'] * NANOS_PER_MILLISECOND,

            # The CPU number
            i
        )

        for i in range(num_cpus)
    ]

    # The migrator is in charge of periodically rebalancing buckets - this is
    # the meat of the time-packing algorithm. We initialize it with the maximum
    # allowable target latency, L_max, as described in our paper.
    migrator = Migrator(json_load['max_latency_millis'], cpus)

    # We periodically recalibrate buckets and migrate processes. How often this
    # happens is controlled by the rebalance_period.
    rebalance_period = (
        json_load['rebalance_period_millis'] * NANOS_PER_MILLISECOND)

    # Continue to simulate while CPUs have unfinished processes.
    while any([c.has_unfinished_procs() for c in cpus]):
        for c in cpus:
            if c.has_unfinished_procs():
                c.run(rebalance_period)

        if json_load['time_packer_active']:
            migrator.rebalance()

    make_runtime_plots(sample_procs)
    report_raw_results(procs, json_load['time_packer_active'], migrator)


def report_raw_results(procs, time_packer_active, migrator):
    """Print statistics about each process."""

    class Stats:
        """Helper class to average context switches for each benchmark."""
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

    if time_packer_active:
        lats = migrator.historical_latencies
        print "Avg latency: {}".format(sum(lats) / len(lats))


def make_runtime_plots(procs):
    """Plot estimated runtimes (moving avg) vs time for each process."""
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
