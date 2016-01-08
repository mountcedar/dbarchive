#!/usr/bin/env python

import pymongo
import mongoengine
import cPickle as pickle
import io
# import bson
# import tempfile
from datetime import datetime
import numpy


class Binary(mongoengine.Document):
    bin = mongoengine.fields.FileField()
    created = mongoengine.fields.DateTimeField()

if __name__ == '__main__':
    con = pymongo.MongoClient()
    con['sample']
    del con
    mongoengine.connect('sample')

    print 'droppnig connection'
    Binary.drop_collection()

    print 'creating new entry'
    for i in range(3):
        entry = Binary()
        with open('xtrain.pkl', 'rb') as fp:
            ary = pickle.load(fp)
        print 'ary: ', ary.shape
        bio = io.BytesIO()
        numpy.save(bio, ary)
        bio.seek(0)
        entry.bin.put(bio)
        entry.created = datetime.now()
        entry.save()

    print 'query and view'
    for obj in Binary.objects.all():
        # bio = io.BytesIO(obj.bin.read())
        ary = numpy.load(obj.bin)
        print 'load array: ', ary.shape
