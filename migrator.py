from jenks import jenks

class Bucket(object):
    def __init__(self, upper_bound):
        self.procs = []
        self.upper_bound = upper_bound
        self.load = 0
        self.num_cpus = 0

    def add_process(self, p):
        self.procs.append(p)
        self.load += p.get_load()

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

        cpus_allotted = 0
        # Each bucket must have at least one CPU
        for b in self.buckets:
            b.num_cpus = 1
            cpus_allotted += 1

        for b in self.buckets:
            cpus_remaining = len(self.cpus) - cpus_allotted
            if cpus_remaining == 0:
                break
            load_weight = b.load / float(total_load)
            cpus_deserved = round(load_weight * len(self.cpus))

            # How many more cpus we should give this bucket
            delta = max(cpus_deserved - b.num_cpus, 0)

            # Grant as many of these cpus as currently possible.
            cpus_granted = min(delta, cpus_remaining)
            cpus_allotted += cpus_granted
            b.num_cpus += cpus_granted


        cpus_remaining = len(self.cpus) - cpus_allotted
        for b in self.buckets:
            cpus_deserved = round(load_weight * len(self.cpus))




        self.print_buckets()

    def print_buckets(self):
        for i, b in enumerate(self.buckets):
            print "Bucket {}".format(i)
            print [p.name for p in b.procs]
            print

