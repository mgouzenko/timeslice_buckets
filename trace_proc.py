#!/usr/bin/python2
import os
import sys
import subprocess

import benchmarks

PERF_DATA = "/tmp/perf.data"

PERF_RECORD = "sudo perf record \
-e sched:sched_stat_sleep \
-e sched:sched_stat_blocked \
-e sched:sched_process_exit \
-a -o {outfile} -- {cmd}"

PERF_SCRIPT = "sudo perf script -i {infile} -F time,event,trace > {outfile}"
PERF_TRACE = "/tmp/perf.trace"

# These are the two possible events that occur when a process sleeps. You can
# look at update_stats_dequeue in fair.c to see this. It looks like the
# sched_stat_wait event occurs when the process is contending for the CPU after
# having been context switched off. But we only care about sleeping patterns.
#
# Note: sched_stat_sleep means the process is interruptible. sched_stat_blocked
# means the process is in an uninterruptible state (probably waiting for IO).
SLEEP_EVENT = "sched_stat_sleep"
BLOCK_EVENT = "sched_stat_blocked"


def main(argv):
    _benchmarks = benchmarks.get_benchmarks()

    if len(argv) != 2:
        print "Usage: ./trace_proc.py <BENCHMARK_NAME>"
        for name, cmd in _benchmarks.iteritems():
            print "{}:\t{}".format(name, cmd)
        return

    bench_name = argv[1]
    command = _benchmarks.get(bench_name, None)
    if command is None:
        print "Invalid benchmark name: {}".format(argv[1])
        return

    print "Running command: {}".format(command)
    run_perf(command)
    parse_trace(bench_name, command, PERF_TRACE)


def parse_trace(bench_name, command, filename):
    """Parse the perf.trace file into csv format.

    Args
        command: the command whose events we're interested in tracing.
        filename: absolute path to the perf.trace file.
    """
    events = []
    command_name = os.path.split(command.split()[0])[1]
    with open(filename, 'r') as trace_file:
        for line in trace_file.readlines():
            # This is a single line of the trace
            split = [i.strip() for i in line.split(':')]
            ts, _, event = split[:3]

            # Resplit the trace on spaces
            trace = '_'.join(split[3:]).split()

            # The command is reported in the trace as "comm=<COMMAND>"
            comm = trace[0].split("=")[1]

            # If this line of the trace is not the command we're interested
            # in, skip it.
            if comm != command_name:
                continue

            stime = (trace[2].split("=")[1]
                     if event == SLEEP_EVENT or event == BLOCK_EVENT else "0")
            events.append(Event(event, ts, stime))

    if not events:
        print "No events captured"
        return

    events.sort(key=lambda e: e.start_time)

    start_time = events[0].start_time

    with open('./traces/{}.trace.csv'.format(bench_name), 'w') as outfile:
        for e in events:
            e.normalize_times(start_time)
            line_out = ','.join([str(e.start_time), e.event_type, str(e.duration)])
            outfile.write(line_out + "\n")


def run_perf(cmd):
    # Trace the command with perf.
    subprocess.call(
        PERF_RECORD.format(
            outfile=PERF_DATA,
            cmd=cmd),
        shell=True)

    # Perf will dump traces to the perf.data file. We must convert the entries
    # into a format that we can parse.
    subprocess.call(
        PERF_SCRIPT.format(infile=PERF_DATA, outfile=PERF_TRACE),
        shell=True)


class Event(object):

    def __init__(self, event_type, end_time, duration):
        self.event_type = event_type

        # Convert the end timestamp to nanos
        self.end_time = int(float(end_time) * (10 ** 9))

        self.duration = int(duration)
        self.start_time = self.end_time - self.duration

    def normalize_times(self, time):
        """Make times relative to 0."""
        self.start_time -= time
        self.end_time -= time


if __name__ == '__main__':
    main(sys.argv)
