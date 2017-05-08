class Scheduler(object):
    def __init__(self, procs, target_latency, migrator):
        self.migrator = migrator

        self.target_latency = target_latency

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
        return self.target_latency / (len(self.waiting_procs) + 1)

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
                                self.target_latency)
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
