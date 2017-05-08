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

    def run(self):
        self.scheduler.run(5000 * self.target_latency)
        self.scheduler.report_results()
