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

        # Procs waiting to take a turn on the CPU
        self.waiting_procs = procs

        # Sleeping procs (waiting for IO and such)
        self.sleeping_procs = []

        # Proc running right now
        self.curr_proc = procs[0]

        self.waiting_procs.remove(self.curr_proc)

        self.time = 0

    def run(self, time):
        # Keep going while any process needs to run.
        while any([not p.finished for p in self.processes]) and time:
            pass

    def min_vruntime_process(self):
        return min(self.processes, key=lambda p: p.vruntime)

    def report_results(self):
        pass

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
        self.vruntime = 0
        self.context_switches = 0
        self.finished = False
        self.state_itr = iter(self.state_list)

        # The first state
        self.curr_state = self.state_itr.next()

    def get_time_to_next_run(self):
        if self.finished:
            return sys.maxint
        elif self.curr_state.state == RUNNING:
            return 0
        else:
            return self.curr_state.duration

    def go_to_next_state(self):
        try:
            self.curr_state = self.state_itr.next()
        except StopIteration:
            self.finished = True

    def run(self, t):
        """Let the process run for time=t.
        
        Return the length of time the process ran. If the process wants to run
        for less than t, the return value is less than t.
        """
        if self.curr_state.state != RUNNING:
            return 0

        time_run = max(self.curr_state.duration, t)
        self.curr_state.duration -= time_run

        if self.curr_state.duration == 0:
            self.go_to_next_state()
                    
        return time_run

    def wait(self, time):
        if self.curr_state != SLEEPING:
            return

        self.curr_state.duration -= max(time, self.curr_state.duration)
        if self.curr_state.duration == 0:
            self.go_to_next_state()

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

    scheduler = Scheduler(procs)
    scheduler.run(5 * (10 ** 9))
    scheduler.report_results()


if __name__ == '__main__':
    main(sys.argv)
