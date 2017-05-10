Mitchell Gouzenko
Andy Xu


Requirements
********************************************************************************
This code has been tested on a Digital Ocean Ubuntu droplet. Since it relies on
parsing perf traces (which vary by installation) it's unlikely to work on other
environments.

In addition, this code uses a cython implementation of Jenks Natural Breaks
Optimization:

    https://github.com/perrygeo/jenks

This can be installed as follows:

    sudo apt-get install build-essential cython python-numpy
    pip install -e "git+https://github.com/perrygeo/jenks.git#egg=jenks"

Finally, this code runs tests from the Phoronix test suite. It expects that the
phoronix-test-suite, along with its aiostress and unpack_linux tests, is
installed:
    sudo apt-get install phoronix-test-suite
    phoronix-test-suite install aio-stress-1.1.1
    phoronix-test-suite install unpack-linux-1.0.0


Collecting traces
********************************************************************************
Before running the simulations, traces must be collected from benchmarks using
the trace_proc.py utility. You can run:

    $ ./trace_proc.py

to get a listing of all the benchmarks, and run:

    $ ./trace_proc.py BENCHMARK_NAME

to run the benchmark and trace its scheduler events with perf. The perf traces
will be converted into a csv file of wake and sleep events, located in ./traces.
The scheduler will use those traces to simulate CFS's scheduling decisions.


Running the scheduler
********************************************************************************
After collecting traces, you can invoke:

    $ ./simulate

to see a list of available workloads. Each workload corresponds to a json
configuration file in the ./workloads directory. This configuration file
specifies:

    1) what traces, and how many instances of each to simulate
    2) various time-packing algorithm parameters
    3) how many cpus to simulate

To run the mixed.json workload, you'd do:

    $ ./simulate mixed

After finishing simulation, the code will output graphs to ./plots and print
context-switching statistics to the console.
