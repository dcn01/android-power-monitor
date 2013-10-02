#!/usr/bin/env python

import time

class Counter(object):

    COUNTER_MINUTE = 0
    COUNTER_HOUR = 1
    COUNTER_DAY = 2
    COUNTER_TOTAL = 3

    # Counter duration in milliseconds
    _COUNTER_DURATION_MINUTE = 60 * 1000
    _COUNTER_DURATION_HOUR = _COUNTER_DURATION_MINUTE * 60
    _COUNTER_DURATION_DAY = _COUNTER_DURATION_HOUR * 24

    COUNTER_DURATIONS = [_COUNTER_DURATION_MINUTE, _COUNTER_DURATION_HOUR,
            _COUNTER_DURATION_DAY, -1]

    def __init__(self):
        self._total = 0
        self._start_time = round(time.time())

        self._counters = {
                COUNTER_MINUTE : _BucketCounter(),
                COUNTER_HOUR : _BucketCounter(),
                COUNTER_DAY : _BucketCounter(),
                COUNTER_TOTAL : _BucketCounter(),
        }

    def add(self, value):
        self._total += value
        now = round(time.time()) - self._start_time
        for type_, counter in self._counters:
            counter.add(value, now * _BucketCounter.BUCKET_NUM /
                    Counter.COUNTER_DURATIONS[type_])

    def get(self, type_):
        assert (Counter.COUNTER_MINUTE <= type_ <= Counter.COUNTER_TOTAL)

        if (type_ == Counter.COUNTER_TOTAL):
            return self._total

        now = round(time.time()) - self._start_time
        timestamp = (now * _BucketCounter.BUCKET_NUM /
                Counter.COUNTER_DURATIONS[type_])
        progress = ((1.0 * now * _BucketCounter.BUCKET_NUM %
                Counter.COUNTER_DURATIONS[type_]) /
                Counter.COUNTER_DURATIONS[type_])
        return self._counters[type_].get(timestamp, progress)

class _BucketCounter(object):
    '''Keep track of data added to timeline for later syncing and summing. Each
    bucket holds a counter for a given second'''

    BUCKET_NUM = 60         # Hold up to 60 seconds of data

    def __init__(self):
        self._buckets = [0] * _BucketCounter.BUCKET_NUM
        self._total = 0
        self._base = 0
        self._base_idx = 0
        self._dropped = 0

    def _sync(self, timestamp):
        '''Synchronize time-based buckets to given timestamp, removing old
        data'''
        self._dropped = 0

        # It's been a while since we synchronized. Let's start freshly new.
        if self._base + 2 * _BucketCounter.BUCKET_NUM <= timestamp:
            # Clear the whole data structure
            self._buckets = [0] * _BucketCounter.BUCKET_NUM
            self._total = 0
            self._base = timestamp
            self._base_idx = 0
        else:
            # Clean the old data buckets holding up to timestamp
            while self._base + _BucketCounter.BUCKET_NUM <= timestamp:
                self._dropped = self._buckets[self._base_idx]
                self._total -= self._dropped
                self._buckets[self._base_idx] = 0
                self._base += 1
                if self._base_idx + 1 == _BucketCounter.BUCKET_NUM:
                    self._base_idx = 0
                else:
                    self._base_idx += 1

    def add(self, value, timestamp):
        '''Add value to bucket corresponding to timestamp'''
        self._sync(timestamp)
        self._total += value
        idx = (self._base_idx + timestamp - self._base)
        if idx >= _BucketCounter.BUCKET_NUM:
            idx -= _BucketCounter.BUCKET_NUM
        self._buckets[idx] += value

    def get(self, timestamp, progress):
        # timestamp gives the time slice that we want information about.
        # progress (between 0 and 1) refers to location inside requested
        # timeslice with 0 indicating that it just started and 1 indicating
        # that it is about to end
        assert (0.0 <= progress <= 1.0)

        self._sync(timestamp)
        return self._total + int((1.0 - progress) * self._dropped)