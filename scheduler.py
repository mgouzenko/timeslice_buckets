#!/usr/bin/python2
import json
import os
import sys

WORKLOAD_DIR = "workloads"
WORKLOAD_FILE_FMT = "./workloads/{}.json"
TRACE_FILE_FMT = "./traces/{}.trace.csv"

RUNNING = 0
SLEEPING = 1
SCHED_WAKEUP = "sched_wakeup"

class Scheduler(object):
    def __init__(self, procs):
        self.processes = procs

class State(object):
    def __init__(self, state, duration):
        self.state = state
        self.duration = int(duration)

    @staticmethod
    def make_state_list_from_trace(trace_name):
        """Parse .trace.csv file (a list of events) as a list of states."""
        states = []

        # The process starts running
        curr_state = RUNNING
        curr_time = 0

        with open(TRACE_FILE_FMT.format(trace_name), "r") as trace_file:
            lineno = 1
            for line in trace_file.readlines():
                event, state, ts = line.split(",")

                # If the current state is running, look for the next sleep
                if curr_state == RUNNING:
                    if event == SCHED_WAKEUP:
                        raise Exception("[line {}] not expecting "
                                        "a wakeup".format(str(lineno)))

                    # We don't care about the context switches that leave this
                    # process still running.
                    if state[0] == "R":
                        continue
                    # D, S, D|S, x, etc
                    else:
                        states.append(State(RUNNING, int(ts) - curr_time))
                        curr_time = int(ts)
                        curr_state = SLEEPING

                # If the current state is sleeping, we look for the next wakeup.
                # In fact, the next wakeup should be the very next event. If
                # not, it's a bug.
                else:
                    if event != SCHED_WAKEUP:
                        raise Exception("[line {}] expected wakeup as next "
                                        "event in trace: {}".format(str(lineno),
                                                                    trace_name))
                    states.append(State(SLEEPING, int(ts) - curr_time))
                    curr_state = RUNNING
                    curr_time = int(ts)

                lineno += 1
        return states


class Process(object):
    def __init__(self, trace_name):
        self.state_list = State.make_state_list_from_trace(trace_name)
        self.print_state_list()
        print

    def print_state_list(self):
        duration = 0
        for state in self.state_list:
            print "{} for {} nanos".format(
                "RUNNING" if state.state == RUNNING else "SLEEPING",
                str(state.duration))
            duration += state.duration

        print "Duration: {} seconds".format(str(float(duration / 10 ** 9)))

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
        for _ in range(proc['quantity']):
            procs.append(Process(proc['benchmark']))


if __name__ == '__main__':
    main(sys.argv)
