RUNNING = 0
SLEEPING = 1
SCHED_WAKEUP = "sched_wakeup"
TARGET_LATENCY = 11 * (10 ** 9)


class State(object):
    def __init__(self, state, duration):
        if state not in [SLEEPING, RUNNING]:
            raise Exception("Bad state")
        self.state = state
        self.duration = int(duration)

    @staticmethod
    def make_state_list_from_trace(trace_name, max_time):
        """Parse .trace.csv file (a list of events) as a list of states."""
        states = []

        # The process starts running
        curr_state = RUNNING
        curr_time = 0

        with open(trace_name, "r") as trace_file:
            lineno = 1
            for line in trace_file.readlines():
                event, state, ts = line.split(",")
                if int(ts) > max_time:
                    break
                duration = int(ts) - curr_time
                # If the current state is running, look for the next sleep
                if curr_state == RUNNING:
                    if event == SCHED_WAKEUP:
                        print ts
                        raise Exception("[line {}] not expecting "
                                        "a wakeup".format(str(lineno)))

                    # We don't care about the context switches that leave this
                    # process still running.
                    if state[0] == "R":
                        continue
                    # D, S, D|S, x, etc
                    else:
                        if duration == 0:
                            duration = 1
                        states.append(State(RUNNING, duration))
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
                    if duration == 0:
                        duration = 1
                    states.append(State(SLEEPING, duration))
                    curr_state = RUNNING
                    curr_time = int(ts)

                lineno += 1
        return states
