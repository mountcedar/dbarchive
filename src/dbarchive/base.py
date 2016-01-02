#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback
import inspect
import numpy
import io
import pymongo
import mongoengine
from bson import Binary


class Base(object):
    @classmethod
    def database(cls, obj=None):
        def getattribute(self, key):
            try:
                v = mongoengine.document.DynamicDocument.__getattribute__(self, key)
                if isinstance(v, Binary):
                    bio = io.BytesIO(v)
                    return numpy.load(bio)
                else:
                    return v
            except:
                logging.error(traceback.format_exc())

        attributes = {}
        # attributes['__getattribute__'] = getattribute
        if not obj is None:
            attributes['__unicode__'] = obj.__unicode__
        else:
            attributes['__getattribute__'] = getattribute
        return type(
            cls.__name__,
            (mongoengine.document.DynamicDocument, ),
            attributes
        )

    def save(self):
        instance = self.database(self)()
        members = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
        attributes = [(k, v) for k, v in members if not(k.startswith('__') and k.endswith('__'))]
        for k, v in attributes:
            if k is 'objects':
                continue
            if isinstance(v, numpy.ndarray):
                bio = io.BytesIO()
                numpy.save(bio, v)
                instance.__setattr__(k, Binary(bio.getvalue()))
            else:
                instance.__setattr__(k, v)
        instance.save()

    class __metaclass__(type):
        @property
        def objects(cls):
            return cls.database().objects


if __name__ == '__main__':
    class Inherit(Base):
        def __init__(self, max=10):
            self.base = "hoge"
            self.bin = numpy.arange(max)

        def __unicode__(self):
            return str(self.__dict__)

    print "create database in mongodb by pymongo"
    con = pymongo.Connection()
    db = con['test_database']
    del con

    print "connecting db with mongoengine"
    mongoengine.connect('test_database')

    print 'create inherit instance'
    inherit = Inherit()
    inherit.save()
    inherit2 = Inherit(3)
    inherit2.save()

    for inherit_ in Inherit.objects.all():
        print 'base: ', inherit_.base if 'base' in inherit_.__dict__ else None
        print 'bin: ', inherit_.bin if 'bin' in inherit_.__dict__ else None

    print "all task completed"
