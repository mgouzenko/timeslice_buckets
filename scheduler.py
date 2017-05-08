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
TARGET_LATENCY = 11 * (10 ** 9)

class Scheduler(object):
    def __init__(self, procs):
        self.processes = procs

        # Procs waiting to take a turn on the CPU
        self.waiting_procs = [p for p in procs]

        # Sleeping procs (waiting for IO and such)
        self.sleeping_procs = []

        # Proc running right now
        self.curr_proc = procs[0]

        self.waiting_procs.remove(self.curr_proc)

        self.residual_time = 0

    def get_timeslice(self):
        """Get the timeslice a process should run for."""
        # According to CFS, all currently waiting processes should be able to
        # run within the target latency. Note that we don't implement weighted
        # priorities as CFS does - every process runs with the same priority.
        if self.curr_proc is None:
            raise Exception("Must have a process to run.")
        return TARGET_LATENCY / (len(self.waiting_procs) + 1)

    def update_sleeping_procs(self, sleep_time):
        for p in self.sleeping_procs:
            p.sleep(sleep_time)

        # Procs that were sleeping but are now running.
        woken_procs = [p for p in self.sleeping_procs if p.is_running()]

        # Gets rid of the procs that are 1) running or 2) finished
        self.sleeping_procs = [p for p in self.sleeping_procs
                               if p.is_sleeping()]

        self.enqueue_procs(woken_procs)

    def enqueue_procs(self, procs):
        # Adjust the timeslice of newly woken processes, just as CFS does in
        # place_entity(). That is, newly woken processes automatically receive
        # the lowest vruntime by a margin of the minimum latency. Sleeps for
        # less than a full latency cycle "don't count" - so processes can't game
        # the scheduler.
        if self.waiting_procs or self.curr_proc is not None:
            if self.waiting_procs:
                min_vruntime = (self.min_vruntime_process().vruntime -
                                TARGET_LATENCY)
            else:
                min_vruntime = self.curr_proc.vruntime

            for p in procs:
                p.vruntime = max(p.vruntime, min_vruntime)

        else:
            # If all processes are sleeping, bring the vruntimes back to 0.
            for p in procs:
                p.vruntime = 0

        # Add the woken procs to the runqueue.
        self.waiting_procs.extend(procs)

    def run(self, time):
        # How long we want to simulate for
        target_sim_time = time + self.residual_time

        # How long we've simulated for
        sim_time = 0

        # Keep going while any process needs to run.
        while any([not p.finished for p in self.processes]):
            time_left = target_sim_time - sim_time

            # If no procs want to run, fast forward time; we need to have a
            # runnable process before we continue with this loop.
            if self.curr_proc is None:
                # Find the min time we need to wait for a process to wake up.
                min_sleep_proc = min(self.sleeping_procs,
                                     key=lambda p: p.curr_state.duration)

                # Cap it at the time remaining in the simulation.
                min_sleep_time = min(min_sleep_proc.curr_state.duration,
                                     time_left)

                # Give the sleeping processes some time to sleep. After this
                # there should be at least one runnable process.
                self.update_sleeping_procs(min_sleep_time)
                sim_time += min_sleep_time

                if not self.waiting_procs:
                    raise Exception("There should be waiting procs by now.")

                self.curr_proc = self.min_vruntime_process()
                self.waiting_procs.remove(self.curr_proc)

                # Try the loop again, now that there's a runnable process.
                continue

            # Figure out how long we should run the current process for.
            ideal_slice = self.get_timeslice()

            # If we don't have enough time to run this slice, break.
            if ideal_slice > time_left:
                self.residual_time = time_left
                break

            # Run it for that time, or until it wants to get off the CPU
            runtime = self.curr_proc.run(ideal_slice)

            sim_time += runtime

            # Mark down the waiting times of all sleeping procs
            self.update_sleeping_procs(runtime)

            # Case 1: curr_proc wants more time, but we need to context switch.
            if self.curr_proc.is_running():
                # If processes are waiting, context switch this one off the CPU
                next_candidate = self.min_vruntime_process()
                if (next_candidate is not None and
                    next_candidate.vruntime < self.curr_proc.vruntime):
                        # Put next_candidate as the current process and put the
                        # current process back on the runqueue.
                        self.curr_proc.context_switches += 1
                        self.waiting_procs.append(self.curr_proc)
                        self.curr_proc = next_candidate
                        self.waiting_procs.remove(next_candidate)

            # 2) curr_proc wants to sleep, so we put it on list of sleepers
            else:
                self.sleeping_procs.append(self.curr_proc)
                self.curr_proc = self.min_vruntime_process()

                # If a process wants to run, remove it from waiting list.
                if self.curr_proc is not None:
                    self.waiting_procs.remove(self.curr_proc)


    def min_vruntime_process(self):
        return (min(self.waiting_procs, key=lambda p: p.vruntime)
                if self.waiting_procs else None)

    def report_results(self):
        for p in self.processes:
            print "{}: {} switches, finished: {}".format(
                p.name, p.context_switches, p.finished)


class State(object):
    def __init__(self, state, duration):
        if state not in [SLEEPING, RUNNING]:
            raise Exception("Bad state")
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
    def __init__(self, trace_name, name):
        self.name = name
        self.state_list = State.make_state_list_from_trace(trace_name)
        self.vruntime = 0
        self.context_switches = 0
        self.finished = False
        self.state_itr = iter(self.state_list)
        self.last_duration = 0

        # The first state
        self.curr_state = self.state_itr.next()

    def is_running(self):
        return (not self.finished) and self.curr_state.state == RUNNING

    def is_sleeping(self):
        return (not self.finished) and self.curr_state.state == SLEEPING

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
            self.last_duration = self.curr_state.duration

        except StopIteration:
            self.finished = True

    def run(self, t):
        """Let the process run for time=t.

        Return the length of time the process ran. If the process wants to run
        for less than t, the return value is less than t.
        """
        if self.curr_state.state != RUNNING:
            return 0

        time_run = min(self.curr_state.duration, t)
        self.curr_state.duration -= time_run

        if self.curr_state.duration == 0:
            self.go_to_next_state()

        # Debit time run.
        self.vruntime += time_run

        return time_run

    def sleep(self, time):
        if self.curr_state.state != SLEEPING:
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
        for i in range(proc['quantity']):
            trace = proc['benchmark']
            procs.append(Process(trace, "{}_{}".format(trace, i)))

    procs[0].print_state_list()

    scheduler = Scheduler(procs)
    scheduler.run(5000 * TARGET_LATENCY)
    scheduler.report_results()


if __name__ == '__main__':
    main(sys.argv)
