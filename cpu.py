from scheduler import Scheduler

class CPU(object):
    def __init__(self, procs, target_latency, number, migrator):
        self.number = number
        self.procs = [p for p in procs]

        for p in self.procs:
            p.cpu = self.number

        self.target_latency = target_latency
        self.scheduler = Scheduler(procs, self.target_latency, migrator)
        migrator.register_cpu(self)

    def has_running_procs(self):
        return any([not p.finished for p in self.procs])

    def run(self, time):
        self.scheduler.run(time)

    def report_results(self):
        self.scheduler.report_results()
