from jenks import jenks

class Bucket(object):
    def __init__(self, upper_bound):
        self.procs = []
        self.upper_bound = upper_bound
        self.load = 0
        self.num_cpus = 0
        self.cpus = []

    def add_process(self, p):
        self.procs.append(p)
        self.load += p.get_load()

    def claim_cpu(self, cpu):
        self.cpus.append(cpu)

    def mark_procs_for_migration(self):
        assert self.num_cpus == len(self.cpus)
        load_map = {c: 0. for c in self.cpus}
        for p in self.procs:
            min_load_cpu = min(load_map.items(), key=lambda i: i[1])[0]
            load_map[min_load_cpu] += p.get_load()
            p.target_cpu = min_load_cpu

        print load_map


class Migrator(object):
    def __init__(self):
        self.cpus = []
        self.buckets = []

    def register_cpu(self, cpu):
        self.cpus.append(cpu)

    def migrate_proc(self, proc):
        pass

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

        bucket_itr = iter(self.buckets)
        curr_bucket = bucket_itr.next()
        for p in procs:
            b = min(self.buckets,
                    key=lambda b: abs(b.upper_bound - p.average_runtime))
            b.add_process(p)

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

    def print_buckets(self):
        for i, b in enumerate(self.buckets):
            print "Bucket {} ({} cpus)".format(i, b.num_cpus)
            print [p.name for p in b.procs]
            print

