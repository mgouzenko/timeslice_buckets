#!/usr/bin/python2
import os
import sys

WORKLOAD_DIR = "workloads"

class State(object):
    def __init__(self, state, duration):
        self.state = state
        self.duration = int(duration)

    @staticmethod
    def make_state_list_from_trace(trace_file):
        pass

class Process(object):
    def __init__(self, trace_name):
        self.state_list = make_state_list_from_trace()

def get_workloads():
    return [f.split(".")[0] for f in os.listdir(WORKLOAD_DIR)]

def list_workloads():
    for f in get_workloads():
        print "\t{}".format(f)

def main(argv):
    if len(argv) != 2:
        print "Usage: ./scheduler.py <WORKLOAD>"
        print
        print "Workloads"
        list_workloads()
        return

    workload = argv[1]
    if workload not in get_workloads():
        print "Unrecognized workload: {}".format(workload)

if __name__ == '__main__':
    main(sys.argv)
