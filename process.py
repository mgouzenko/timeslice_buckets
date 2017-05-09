import sys
import matplotlib.pyplot as plt

from state import State, RUNNING, SLEEPING

N_LATENCIES = 10


class Process(object):
    def __init__(self, trace_file_name, name, time):
        self.target_latency = 0
        self.name = name

        # Current CPU the process is running on
        self.curr_cpu = None

        # CPU the process should migrate to
        self.destination_cpu = None
        self.needs_migration = False

        # A parsing of the process's trace into a list of states.
        self.state_list = State.make_state_list_from_trace(trace_file_name, time)
        self.state_itr = iter(self.state_list)

        self.vruntime = 0

        self.total_runtime = 0
        self.total_sleeptime = 0

        self.context_switches = 0
        self.finished = False
        self.last_duration = 0

        # How long the process has been running since it last woke.
        self.curr_runtime = 0
        self.average_runtime = 0
        self.average_runtime_points = []
        self.runtime_points = []

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

    def calc_average_runtime(self):
        # Return the average of the last N runtimes.
        wall_clock_time = self.total_runtime + self.total_sleeptime

        # Average the runtimes available to us in the last N_LATENCIES latency
        # cycles.
        last_n = [p[1] for p in self.runtime_points
                  if wall_clock_time - p[0] <
                  (N_LATENCIES * self.target_latency)]
        last_n.append(self.curr_runtime)

        return sum(last_n) / len(last_n)

    def go_to_next_state(self):
        try:
            self.curr_state = self.state_itr.next()
            self.last_duration = self.curr_state.duration

            # If we go from running --> sleeping, update the average runtime.
            if self.curr_state.state == SLEEPING:
                self.average_runtime = self.calc_average_runtime()

                # What the wall clock time would be if this process were run in
                # isolation.
                wall_clock_time = self.total_runtime + self.total_sleeptime
                self.runtime_points.append((wall_clock_time, self.curr_runtime))
                self.average_runtime_points.append((wall_clock_time,
                                                    self.average_runtime))
                self.curr_runtime = 0
        except StopIteration:
            self.finished = True

    def run(self, t):
        """Let the process run for time=t.

        Return the length of time the process ran. If the process wants to run
        for less than t, the return value is less than t.
        """

        assert self.curr_state.state == RUNNING

        time_run = min(self.curr_state.duration, t)
        if time_run <= 0:
            print "WRSFGSDAFDSA"
            print time_run
            print self.curr_state.duration
        assert time_run > 0

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
            self.average_runtime = self.calc_average_runtime()

        self.adjust_state()

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

    def adjust_state(self):
        if self.curr_state.duration == 0:
            self.go_to_next_state()
        elif self.curr_state.duration < 0:
            raise Exception("Duration of curr_state should not be negative.")

    def sleep(self, time):
        if self.curr_state.state != SLEEPING:
            return

        time_sleep = min(time, self.curr_state.duration)
        assert time_sleep > 0

        self.curr_state.duration -= time_sleep
        self.total_sleeptime += time_sleep

        self.adjust_state()

    def print_state_list(self):
        duration = 0
        for state in self.state_list:
            print "{} for {} nanos".format(
                "RUNNING" if state.state == RUNNING else "SLEEPING",
                str(state.duration))
            duration += state.duration

        print "Duration: {} seconds".format(str(float(duration / 10 ** 9)))

    def make_plots(self, root):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot([p[0] for p in self.average_runtime_points],
                [p[1] for p in self.average_runtime_points])
        fig.savefig('{}/{}.png'.format(root, self.name))
