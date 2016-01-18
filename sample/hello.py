#!/usr/bin/env python

import logging
import numpy
from datetime import datetime
from dbarchive import Base


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    class Sample(Base):
        def __init__(self, maxval=10):
            self.base = "hoge"
            self.bin = numpy.arange(maxval)
            self.created = datetime.now()

    print 'dropping past sample collection'
    Sample.drop_collection()

    print 'create sample instance'
    sample01 = Sample(10)
    sample01.save()
    sample02 = Sample(3)
    sample02.save()

    print "query mongodb with custom constructor"
    for sample in Sample.objects.all():
        print 'sample: ', type(sample)
        print '\tbase: ', sample.base, type(sample.base)
        print '\tbin: ', sample.bin, type(sample.bin)
        print '\tcreated: ', sample.created, type(sample.created)

    print 'updating sample object'
    sample01.bin = numpy.arange(20)
    sample01.save()

    print "confirming the variable 'bin' is updated."
    for sample in Sample.objects.all():
        print 'sample: ', type(sample)
        print '\tbase: ', sample.base, type(sample.base)
        print '\tbin: ', sample.bin, type(sample.bin)
        print '\tcreated: ', sample.created, type(sample.created)

    print "query mongodb without custom constructor"
    for sample in Sample.native_objects().all():
        print 'sample: ', type(sample)
        print '\tbase: ', sample.base, type(sample.base)
        print '\tbin: ', sample.bin if 'bin' in sample.__dict__ else 'bin object is not found.'
        print '\tcreated: ', sample.created, type(sample.created)

    print "all task completed"