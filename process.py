from state import State, RUNNING, SLEEPING

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
        self.context_switches = 0
        self.finished = False
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
