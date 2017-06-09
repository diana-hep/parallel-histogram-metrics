import sys
import ctypes
import threading
import time

import numpy
import psutil

size = int(int(sys.argv[1]) * 1024**3 / 8)    # 1024**3 / 8 == 2**27
trials = int(float(sys.argv[2]))
cardinality = size >> int(sys.argv[3])

fillme = numpy.zeros(size, dtype=numpy.int64)
startgun = threading.Event()

libc = ctypes.cdll.LoadLibrary("libc.so.6")
randomfill = ctypes.cdll.LoadLibrary("randomfill.so")

GETTID = 186   # from /usr/include/asm/unistd_64.h

randomfill.naive.argtypes = (ctypes.POINTER(ctypes.c_long), ctypes.c_long, ctypes.c_long, ctypes.c_long)
randomfill.naive.restype = ctypes.c_double

randomfill.atomic.argtypes = (ctypes.POINTER(ctypes.c_long), ctypes.c_long, ctypes.c_long, ctypes.c_long)
randomfill.atomic.restype = ctypes.c_double

randomfill.cassafe.argtypes = (ctypes.POINTER(ctypes.c_long), ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_long))
randomfill.cassafe.restype = ctypes.c_double

class RunNaive(threading.Thread):
    def __init__(self, index, fillme, size, trials, cardinality, startgun):
        super(RunNaive, self).__init__()
        self.index = index
        self.fillme = fillme
        self.size = size
        self.trials = trials
        self.cardinality = cardinality
        self.startgun = startgun

    def run(self):
        # pinning ensures that they start and end at the same time
        pid = libc.syscall(GETTID)
        psutil.Process(pid).cpu_affinity([self.index])
        
        fillme = self.fillme.ctypes.data_as(ctypes.POINTER(ctypes.c_long))
        size = ctypes.c_long(self.size)
        trials = ctypes.c_long(self.trials)
        cardinality = ctypes.c_long(self.cardinality)

        # print(self.name, pid, "ready")
        self.startgun.wait()
        self.time = randomfill.naive(fillme, size, trials, cardinality)
        self.collisions = 0

class RunAtomic(threading.Thread):
    def __init__(self, index, fillme, size, trials, cardinality, startgun):
        super(RunAtomic, self).__init__()
        self.index = index
        self.fillme = fillme
        self.size = size
        self.trials = trials
        self.cardinality = cardinality
        self.startgun = startgun

    def run(self):
        # pinning ensures that they start and end at the same time
        pid = libc.syscall(GETTID)
        psutil.Process(pid).cpu_affinity([self.index])
        
        fillme = self.fillme.ctypes.data_as(ctypes.POINTER(ctypes.c_long))
        size = ctypes.c_long(self.size)
        trials = ctypes.c_long(self.trials)
        cardinality = ctypes.c_long(self.cardinality)

        # print(self.name, pid, "ready")
        self.startgun.wait()
        self.time = randomfill.atomic(fillme, size, trials, cardinality)
        self.collisions = 0

class RunCASSafe(threading.Thread):
    def __init__(self, index, fillme, size, trials, cardinality, startgun):
        super(RunCASSafe, self).__init__()
        self.index = index
        self.fillme = fillme
        self.size = size
        self.trials = trials
        self.cardinality = cardinality
        self.startgun = startgun

    def run(self):
        # pinning ensures that they start and end at the same time
        pid = libc.syscall(GETTID)
        psutil.Process(pid).cpu_affinity([self.index])

        fillme = self.fillme.ctypes.data_as(ctypes.POINTER(ctypes.c_long))
        size = ctypes.c_long(self.size)
        trials = ctypes.c_long(self.trials)
        cardinality = ctypes.c_long(self.cardinality)
        collisions = ctypes.c_long(0)
        p_collisions = ctypes.POINTER(ctypes.c_long)(collisions)

        # print(self.name, pid, "ready")
        self.startgun.wait()
        self.time = randomfill.cassafe(fillme, size, trials, cardinality, p_collisions)
        self.collisions = collisions.value

# experiment = numpy.random.permutation([(i, "naive", RunNaive) for i in range(1, 128+1)] + [(i, "cassafe", RunCASSafe) for i in range(1, 128+1)])   # [(128, "cassafe", RunCASSafe)]
# experiment = numpy.random.permutation([(i, "naive", RunNaive) for i in range(1, 64+1)] + [(i, "cassafe", RunCASSafe) for i in range(1, 64+1)])

experiment = numpy.random.permutation([(i, "naive", RunNaive) for i in range(1, 128+1)] + [(i, "atomic", RunAtomic) for i in range(1, 128+1)])

cpus = numpy.random.permutation(list(range(128)))

fileName = "results_{}_{}_{}.txt".format(sys.argv[1], sys.argv[2], sys.argv[3])
outputFile = open(fileName, "w")

for numThreads, whichname, which in experiment:
    threads = []
    for index in range(numThreads):
        threads.append(which(int(cpus[index]), fillme, size, trials, cardinality, startgun))
        threads[-1].start()
    # print(psutil.Process().threads())

    time.sleep(3)   # plenty of time for everybody to get ready; can see that in the printouts

    # print("go!")
    startgun.set()

    for x in threads:
        x.join()

    meantime = numpy.mean([float(x.time) for x in threads])
    rate = trials * numThreads / meantime / 1e6   # MHz
    deviations = numpy.std([float(x.time) for x in threads]) / meantime
    collisions = sum(x.collisions for x in threads) / float(trials * numThreads)
    print("{}\t{}\t{}\t{}\t{}".format(whichname, numThreads, rate, deviations, collisions))
    outputFile.write("{}\t{}\t{}\t{}\t{}\n".format(whichname, numThreads, rate, deviations, collisions))

outputFile.close()
