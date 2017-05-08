from state import State, RUNNING, SLEEPING

ALPHA = 0.3

class Process(object):
    def __init__(self, trace_file_name, name):
        self.name = name

        # Current CPU the process is running on
        self.curr_cpu = None

        # CPU the process should migrate to
        self.destination_cpu = None
        self.needs_migration = False

        # A parsing of the process's trace into a list of states.
        self.state_list = State.make_state_list_from_trace(trace_file_name)
        self.state_itr = iter(self.state_list)

        self.vruntime = 0

        self.total_runtime = 0
        self.total_sleeptime = 0

        self.context_switches = 0
        self.finished = False
        self.last_duration = 0

        # How long the process has been running since it last woke.
        self.curr_runtime = 0
        self.old_average_runtime = 0
        self.average_runtime = 0

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

            # If we go from running --> sleeping, update the average runtime.
            if self.curr_state.state == SLEEPING:
                self.average_runtime = ((ALPHA * self.old_average_runtime) +
                                        (1. - ALPHA) * self.curr_runtime)
                self.old_average_runtime = self.average_runtime
                self.curr_runtime = 0
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
        self.curr_runtime += time_run

        # Note: runtime is how long the process has run since it woke up.
        #
        # This provision is in place for processes that never sleep. We
        # calculate the average runtime as a function of the previous average
        # runtime and the last runtime.
        #
        # Thus, when the process goes to sleep, we have a concrete
        # "last runtime" and can update the average runtime accordingly.
        #
        # This problematic because the frequency with which the average runtime
        # is updated depends on how long the process runs for before it goes to
        # sleep. If the process never goes to sleep, the average runtime will
        # never get updated!
        #
        # To fix this, we update the average runtime whenever the process gets
        # off the cpu. If it has been on the CPU for longer than average, we
        # use the current runtime to estimate the "last runtime".
        if self.curr_runtime > self.average_runtime:
            self.average_runtime = ((ALPHA * self.old_average_runtime) +
                                    (1. - ALPHA) * self.curr_runtime)

        if self.curr_state.duration == 0:
            self.go_to_next_state()

        # Debit time run.
        self.vruntime += time_run
        self.total_runtime += time_run

        return time_run

    def get_load(self):
        """Measure the load a process puts on the CPU.

        The metric we use is ratio of voluntary runtime to total time spent
        running or sleeping (but not waiting).
        """
        return (float(self.total_runtime) /
                (self.total_runtime + self.total_sleeptime))

    def sleep(self, time):
        if self.curr_state.state != SLEEPING:
            return

        time_sleep = max(time, self.curr_state.duration)
        self.curr_state.duration -= time_sleep
        self.total_sleeptime += time_sleep

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
