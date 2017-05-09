#!/usr/bin/python2
import os
import re
import sys
import subprocess

import benchmarks

PERF_DATA = "/tmp/{}/perf.data".format(os.getuid())

PERF_RECORD = "sudo perf record \
-e sched:sched_switch \
-e sched:sched_wakeup \
-e sched:sched_process_exit \
-a -o {outfile} -- {cmd}"

PERF_SCRIPT = "sudo perf script -i {infile} -F time,event,trace > {outfile}"
PERF_TRACE = "/tmp/{}/perf.trace".format(os.getuid())

WAKE_EVENT = "sched_wakeup"
SWITCH_EVENT = "sched_switch"
TRACE_DIR = "./traces"


def main(argv):
    _benchmarks = benchmarks.BENCHMARKS

    if len(argv) != 2:
        print "Usage: ./trace_proc.py <BENCHMARK_NAME>"
        for name, b in _benchmarks.iteritems():
            print "{}:\t{}".format(name, b.benchmark_cmd)
        return

    if not os.path.isdir("/tmp/{}".format(os.getuid())):
        os.mkdir("/tmp/{}".format(os.getuid()))

    bench_name = argv[1]
    bench = _benchmarks.get(bench_name, None)
    if bench is None:
        print "Invalid benchmark name: {}".format(argv[1])
        return

    if bench.preparation_cmd is not None:
        print "Running preparation command: {}".format(bench.preparation_cmd)
        subprocess.call(bench.preparation_cmd, shell=True)

    perf_record(bench.benchmark_cmd)
    perf_script()

    if not os.path.isdir(TRACE_DIR):
        os.mkdir(TRACE_DIR)

    parse_trace(bench_name, bench.benchmark_cmd, PERF_TRACE)


def parse_trace(bench_name, command, filename):
    """Parse the perf.trace file into csv format.

    Args
        command: the command whose events we're interested in tracing.
        filename: absolute path to the perf.trace file.
    """
    # dict of pid -> event list. This is here because sometimes processes fork
    # off children.
    events = {}
    command_name = os.path.split(command.split()[0])[1]
    with open(filename, 'r') as trace_file:
        for line in trace_file.readlines():
            # This is a single line of the trace
            split = [i.strip() for i in line.split(' ') if i.strip()]

            raw_ts, raw_event = split[:2]
            event = raw_event.split(":")[1].strip()
            ts = raw_ts.split(":")[0].strip()
            trace = " ".join(split[2:])
            state = trace.split("=")[0].split()[-1]

            cmd = None
            if event == SWITCH_EVENT:
                cmd = re.search("prev_comm=(\S*)", trace).group(1)
                pid = re.search("prev_pid=(\d*)", trace).group(1)
                state = re.search("prev_state=(\S*)", trace).group(1)

            elif event == WAKE_EVENT:
                cmd = re.search("comm=(\S*)", trace).group(1)
                pid = re.search("pid=(\d*)", trace).group(1)
                state = ""

            # If this line of the trace is not the command we're interested
            # in, skip it.
            if cmd != command_name:
                continue

            events.setdefault(pid, []).append(Event(event, ts, state, trace))

    if not events:
        print "No events captured"
        return

    event_list = []

    # Get the longest list of events (this is probably the PID we care about)
    for pid, elist in events.iteritems():
        if len(elist) > len(event_list):
            event_list = elist

    event_list.sort(key=lambda e: e.time)

    start_time = event_list[0].time

    with open('./traces/{}.trace.csv'.format(bench_name), 'w') as outfile:
        for e in event_list:
            e.normalize_time(start_time)
            line_out = ','.join([e.event_type, e.state, str(e.time)])
            outfile.write(line_out + "\n")


def perf_record(cmd):
    # Trace the command with perf.
    subprocess.call(
        PERF_RECORD.format(
            outfile=PERF_DATA,
            cmd=cmd),
        shell=True)

def perf_script():
    # Perf will dump traces to the perf.data file. We must convert the entries
    # into a format that we can parse.
    subprocess.call(
        PERF_SCRIPT.format(infile=PERF_DATA, outfile=PERF_TRACE),
        shell=True)


class Event(object):

    def __init__(self, event_type, time, state, trace):
        self.event_type = event_type

        # Convert the end timestamp (which is now in seconds) to nanos
        self.time = int(float(time) * (10 ** 9))

        self.state = state
        self.trace = trace

    def normalize_time(self, time):
        """Make times relative to 0."""
        self.time -= time


if __name__ == '__main__':
    main(sys.argv)
