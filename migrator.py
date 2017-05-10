from jenks import jenks

# 100 nanos rounding error
ROUNDING_ERROR = 100
MAX_TARGET_LATENCY = 100 * (10 ** 6)
NORMALIZING_FACTOR = 4

class Bucket(object):
    def __init__(self, upper_bound):
        self.procs = []
        self.upper_bound = upper_bound
        self.load = 0
        self.num_cpus = 0
        self.cpus = []
        self.desired_latencies = {}

    def add_process(self, p):
        self.procs.append(p)
        self.load += p.get_load()

    def claim_cpu(self, cpu):
        self.cpus.append(cpu)

    def mark_procs_for_migration(self):
        assert self.num_cpus == len(self.cpus)
        load_map = {c: 0. for c in self.cpus}
        self.desired_latencies = {c: 0. for c in self.cpus}

        for p in self.procs:
            min_load_cpu = min(load_map.items(), key=lambda i: i[1])[0]
            load_map[min_load_cpu] += p.get_load()
            p.target_cpu = min_load_cpu
            self.desired_latencies[min_load_cpu] += p.average_runtime

    def set_new_latencies(self, max_latency):
        for c in self.cpus:
            lat = min(self.desired_latencies[c],
                              max_latency)
            c.scheduler.target_latency = lat


class Migrator(object):
    def __init__(self, max_latency_millis):
        self.cpus = []
        self.buckets = []
        self.max_latency = max_latency_millis * (10 ** 6)
        self.historical_latencies = []

    def register_cpu(self, cpu):
        self.cpus.append(cpu)

    def gather_procs(self):
        """Get all the processes running on all CPUs."""
        procs = []
        for c in self.cpus:
            procs.extend(c.scheduler.sleeping_procs)
            procs.extend(c.scheduler.waiting_procs)
            if c.scheduler.curr_proc is not None:
                procs.append(c.scheduler.curr_proc)

        return procs

    def rebalance(self):
        """Flag processes for migration based on their workloads."""
        num_buckets = len(self.cpus) / 2
        procs = self.gather_procs()

        # The processes should all be finished.
        if len(procs) == 0:
            return

        bucket_boundaries = jenks([p.average_runtime for p in procs],
                                  min(num_buckets, len(procs)))

        self.buckets = [Bucket(int(b)) for b in bucket_boundaries[1:]]
        assert len(self.buckets) > 0

        # Classify each process in a bucket
        for p in procs:
            bucket_found = False
            for b in self.buckets:
                if p.average_runtime - ROUNDING_ERROR <= b.upper_bound:
                    b.add_process(p)
                    bucket_found = True
                    break

            # This can occur due to rounding error
            if not bucket_found:
                self.buckets[-1].add_process(p)

        total_load = sum([b.load for b in self.buckets])

        # How many cpus we've given to the buckets
        cpus_allotted = 0

        # How many cpus we seek to distributed. It doesn't make sense to
        # distribute more cpus than processes.
        target_allotted = min(len(procs), len(self.cpus))

        # Each bucket must have at least one CPU if it has processes.
        for b in self.buckets:
            if b.procs:
                b.num_cpus = 1
                cpus_allotted += 1

        for b in self.buckets:
            if not b.procs:
                continue

            cpus_remaining = target_allotted - cpus_allotted
            if cpus_remaining == 0:
                break
            load_weight = b.load / total_load
            cpus_deserved = int(round(load_weight * len(self.cpus)))

            # How many more cpus we should give this bucket
            delta = max(cpus_deserved - b.num_cpus, 0)

            # Grant as many of these cpus as currently possible.
            cpus_granted = min(delta, cpus_remaining, len(b.procs) - 1)
            cpus_allotted += cpus_granted
            b.num_cpus += cpus_granted


        cpus_remaining = target_allotted - cpus_allotted
        for b in sorted(self.buckets, key=lambda b: -b.load):
            if cpus_remaining == 0:
                break

            if len(b.procs) > b.num_cpus:
                b.num_cpus += 1
                cpus_remaining -= 1

        assert cpus_remaining == 0

        cpu_itr = iter(self.cpus)
        for b in self.buckets:
            for _ in range(b.num_cpus):
                cpu = cpu_itr.next()
                b.claim_cpu(cpu)

            b.mark_procs_for_migration()

        self.print_buckets()

        for c in self.cpus:
            c.scheduler.migrate_procs()

        for b in self.buckets:
            b.set_new_latencies(self.max_latency)

        avg_latency = (sum([c.scheduler.target_latency for c in self.cpus]) /
                       len(self.cpus))

        self.historical_latencies.append(avg_latency)


    def print_buckets(self):
        for i, b in enumerate(self.buckets):
            print "Bucket {} ({} cpus): {}".format(i, b.num_cpus, b.upper_bound)
            for p in b.procs:
                print "\t{}: {}".format(p.name, p.average_runtime)
            print
