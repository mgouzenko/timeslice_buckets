from scheduler import Scheduler

class CPU(object):
    def __init__(self, procs, target_latency, number, migrator):
        self.number = number

        for p in procs:
            p.target_cpu = self

        self.target_latency = target_latency
        self.scheduler = Scheduler(procs, self.target_latency, migrator)
        migrator.register_cpu(self)

    def has_unfinished_procs(self):
        return any([not p.finished for p in self.scheduler.processes])

    def get_unfinished_procs(self):
        return [p for p in self.scheduler.processes if not p.finished]

    def run(self, time):
        self.scheduler.run(time)
