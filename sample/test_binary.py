#!/usr/bin/env python

import pymongo
import mongoengine
import cPickle as pickle
import io
# import bson
# import tempfile
from datetime import datetime
import numpy


class Binary(mongoengine.DynamicDocument):
    # top = mongoengine.fields.ReferenceField()
    parent = mongoengine.fields.ObjectIdField()
    variable_name = mongoengine.fields.StringField()
    bin = mongoengine.fields.FileField()
    created = mongoengine.fields.DateTimeField()


class Top(mongoengine.DynamicDocument):
    pass

if __name__ == '__main__':
    con = pymongo.MongoClient()
    con['sample']
    del con
    mongoengine.connect('sample')

    print 'droppnig connection'
    Binary.drop_collection()

    print 'creating new entry'
    for i in range(1):
        top = Top()
        top.name = 'hoge'
        top.save()
        entry = Binary()
        with open('xtrain.pkl', 'rb') as fp:
            ary = pickle.load(fp)
        print 'ary: ', ary.shape
        bio = io.BytesIO()
        # numpy.save(bio, ary)
        pickle.dump(ary, bio)
        bio.seek(0)
        # entry.bin.put(bio)
        entry.bin = bio
        entry.created = datetime.now()
        entry.variable_name = 'hoge'
        print 'top pk: ', top.pk, type(top.pk)
        entry.parent = top.pk
        entry.save()

    print 'query and view'
    for obj in Top.objects.all():
        # bio = io.BytesIO(obj.bin.read())
        print 'obj pk: ', obj.pk, type(obj.pk)
        binary = Binary.objects.filter(parent=obj.pk, variable_name='hoge').first()
        print 'binary: ', binary
        ary = pickle.load(binary.bin)
        print 'load array: ', ary.shape
