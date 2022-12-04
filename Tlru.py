# Dara
from time import time, sleep
from collections import OrderedDict


class TLRU_Table:
    def __init__(self, size, count=1):
        self.vals = OrderedDict()
        self.times = {}
        self.counts = {}
        self.size = size

    def contains(self, data_name):
        self.evalutateTTU()
        if data_name in self.vals:
            return True
        else:
            return False

    def evalutateTTU(self):
        for data_name, use_time in self.times.copy().items():
            if time() > use_time:
                self.vals.pop(data_name)
                self.times.pop(data_name)

    def get(self, data_name):
        self.vals.move_to_end(data_name)
        return self.vals[data_name], self.times[data_name]

    def removeLRU(self):
        (k, v) = self.vals.popitem(last=False)
        self.times.pop(k)
        self.counts.pop(k)

    def add(self, data_name, data_val, ttu=32500000000, count=1):
        if time() > ttu:
            return
        elif self.contains(data_name):
            if ttu < self.times[data_name]:
                return
        elif len(self.vals) >= self.size:
            self.removeLRU()
        self.times[data_name] = ttu
        self.vals[data_name] = data_val
        self.counts[data_name] = count

    def removeCount(self, data_name):
        if self.contains(data_name):
            if self.counts[data_name] == 1:
                val = self.vals.pop(data_name)
                self.times.pop(data_name)
                self.counts.pop(data_name)
                return val, 0
            else:
                self.counts[data_name] -= 1
                return self.vals[data_name], self.counts[data_name]
        return None, -1

    def remove(self, data_name):
        if self.contains(data_name):
            val = self.vals.pop(data_name)
            self.times.pop(data_name)
            self.counts.pop(data_name)
            return val, 0
        else:
            return None, -1

    def __str__(self):
        return str(self.vals) + '\n' + str(self.counts)

    def __iter__(self):
        return iter(self.vals)
