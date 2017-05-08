class Migrator(object):
    def __init__(self):
        self.cpus = []

    def register_cpu(self, cpu):
        self.cpus.append(cpu)

    def flag_procs_for_migration(self):
        pass

    def migrate_proc(self, proc):
        pass
