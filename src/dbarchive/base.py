#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import inspect
import cPickle as pickle
from abc import ABCMeta
from abc import abstractmethod
from datetime import datetime
import logging
#import traceback

import numpy
import pymongo
import mongoengine
from mongoengine.document import Document
from mongoengine.document import DynamicDocument
from mongoengine import fields
from bson import Binary


def connect(database="__py_dbarchive", *args, **kwargs):
    con = pymongo.Connection(*args, **kwargs)
    con[database]
    del con
    mongoengine.connect(database, *args, **kwargs)


class LargeBinary(DynamicDocument):
    binary = fields.FileField()
    created = fields.DateTimeField()


class Archiver(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def dump(self):
        return None

    @abstractmethod
    def restore(self):
        return None

    @classmethod
    def post_dump(cls, f):
        def _filter(self, obj):
            ret = f(self, obj)
            if len(ret) > 16 * 1024 ** 2:
                entry = LargeBinary()
                bio = io.BytesIO(ret)
                entry.binary.put(bio)
                entry.created = datetime.now()
                entry.save()
                return entry
            else:
                return ret
        return _filter

    @classmethod
    def pre_restore(cls, f):
        def _filter(self, obj):
            if isinstance(obj, LargeBinary):
                logging.debug('large binary instance coming')
                return f(self, Binary(obj.binary.read()))
            else:
                return f(self, obj)
        return _filter


class PickleArchiver(Archiver):
    @Archiver.post_dump
    def dump(self, obj):
        bio = io.BytesIO()
        pickle.dump(obj, bio)
        return Binary(bio.getvalue())

    @Archiver.pre_restore
    def restore(self, obj):
        return pickle.load(io.BytesIO(obj))


class NpyArchiver(Archiver):
    @Archiver.post_dump
    def dump(self, obj):
        bio = io.BytesIO()
        numpy.save(bio, obj)
        return Binary(bio.getvalue())

    @Archiver.pre_restore
    def restore(self, obj):
        return numpy.load(io.BytesIO(obj))


class Base(object):
    valid_classes = [int, float, long, bool, str, list, tuple, dict]
    default_archiver = PickleArchiver()

    def __init__(self):
        self.excludes = ['valid_classes', 'default_archiver', 'excludes', 'archivers', 'objects']
        self.archivers = {numpy.ndarray: NpyArchiver()}

    @classmethod
    def database(cls, obj=None):
        def getattribute(self, key):
            v = object.__getattribute__(self, key)
            try:
                archivers = object.__getattribute__(self, 'archivers')
                if key in archivers:
                    archiver = eval(archivers[key])()
                    return archiver.restore(v)
                else:
                    return v
            except:
                # logging.error(traceback.format_exc())
                return v
        attributes = {'meta': {'max_size': 1024**3}}
        if obj is None:
            attributes['__getattribute__'] = getattribute
        return type(
            cls.__name__ + "Table",
            (DynamicDocument, ),
            attributes
        )

    def save(self):
        instance = self.database(self)()
        members = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
        attributes = [(k, v) for k, v in members if not k.startswith('_')]
        archivers = {}
        for k, v in attributes:
            if k in self.excludes:
                continue
            if type(v) in self.valid_classes:
                logging.debug("set attribute default: {}, {}".format(k, type(v)))
                instance.__setattr__(k, v)
            elif type(v) in self.archivers.keys():
                logging.debug("set attribute customly binalized: {}, {}".format(k, type(v)))
                archiver = self.archivers[type(v)]
                archivers[k] = archiver.__class__.__name__
                binary = archiver.dump(v)
                instance.__setattr__(k, binary)
            else:
                logging.debug("set attribute pickled: {}, {}".format(k, type(v)))
                archivers[k] = self.default_archiver.__class__.__name__
                binary = self.default_archiver.dump(v)
                instance.__setattr__(k, binary)
        instance.__setattr__('archivers', archivers)
        instance.save(validate=False)

    class __metaclass__(type):
        @property
        def objects(cls):
            return cls.database().objects


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    class Sample(Base):
        def __init__(self, max=10):
            Base.__init__(self)
            self.base = "hoge"
            self.bin = numpy.arange(max)

    connect()
    print 'create inherit instance'
    sample01 = Sample(max=10)
    sample01.save()
    sample02 = Sample(max=3)
    sample02.save()

    for sample in Sample.objects.all():
        print 'base: ', sample.base
        print 'bin: ', sample.bin

    print "all task completed"
