#!/usr/bin/python2
import sys
import subprocess

PERF_DATA = "/tmp/perf.data"
PERF_RECORD = "sudo perf record -e sched:sched_stat_sleep -e\
sched:sched_stat_blocked -e sched:sched_process_exit -a -o {outfile} -- {cmd}"
PERF_SCRIPT="sudo perf script -i {infile} > {outfile}"
PERF_TRACE="/tmp/perf.trace"

def main(argv):
    if len(argv) < 2:
        print "Usage: ./trace_proc.py"

    # Trace the command with perf.
    subprocess.call(
        PERF_RECORD.format(
            outfile=PERF_DATA,
            cmd=' '.join(argv[1:])),
        shell=True)

    # Perf will dump traces to the perf.data file. We must convert the entries
    # into a format that we can parse.
    subprocess.call(
        PERF_SCRIPT.format(infile=PERF_DATA, outfile=PERF_TRACE),
        shell=True)

if __name__ == '__main__':
    main(sys.argv)
