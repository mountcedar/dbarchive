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

    for sample in Sample.objects.all():
        print 'sample: ', type(sample)
        print '\tbase: ', sample.base
        print '\tbin: ', sample.bin
        print '\tcreated: ', sample.created

    sample01.bin = numpy.arange(20)
    sample01.save()

    for sample in Sample.objects.all():
        print 'sample: ', type(sample)
        print '\tbase: ', sample.base
        print '\tbin: ', sample.bin
        print '\tcreated: ', sample.created

    print "all task completed"
