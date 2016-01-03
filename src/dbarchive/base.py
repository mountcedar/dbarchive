#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import inspect
import cPickle as pickle
from abc import ABCMeta
from abc import abstractmethod
import logging
import traceback

import numpy
import pymongo
import mongoengine
from mongoengine.document import Document
from mongoengine.document import DynamicDocument
from mongoengine import fields
from bson import Binary


def connect(database="__py_dbarchive", *args, **kwargs):
    con = pymongo.Connection()
    con[database]
    del con
    mongoengine.connect(database)


class LargeBinary(Document):
    parent = fields.ReferenceField('Base')
    binary = fields.FileField()


class Archiver(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def serialize(self):
        return None

    @abstractmethod
    def deserialize(self):
        return None

    @classmethod
    def check_size(cls, f):
        def check_and_exec(*args, **kwargs):
            ret = f(*args, **kwargs)
            if len(ret) > 16 * 1024 ** 2:
                raise Exception('binary size is too large.')
            return ret
        return check_and_exec


class PickleArchiver(Archiver):
    @Archiver.check_size
    def serialize(self, obj):
        bio = io.BytesIO()
        pickle.dump(obj, bio)
        return Binary(bio.getvalue())

    def deserialize(self, obj):
        return pickle.load(io.BytesIO(obj))


class NpyArchiver(Archiver):
    @Archiver.check_size
    def serialize(self, obj):
        bio = io.BytesIO()
        numpy.save(bio, obj)
        return Binary(bio.getvalue())

    def deserialize(self, obj):
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
                    return archiver.deserialize(v)
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
                print "set attribute default: ", k, type(v)
                instance.__setattr__(k, v)
            elif type(v) in self.archivers.keys():
                print "set attribute customly binalized: ", k, type(v)
                archiver = self.archivers[type(v)]
                archivers[k] = archiver.__class__.__name__
                binary = archiver.serialize(v)
                instance.__setattr__(k, binary)
            else:
                print "set attribute pickled: ", k, type(v)
                archivers[k] = self.default_archiver.__class__.__name__
                binary = self.default_archiver.serialize(v)
                instance.__setattr__(k, binary)
        instance.__setattr__('archivers', archivers)
        instance.save()

    class __metaclass__(type):
        @property
        def objects(cls):
            return cls.database().objects


if __name__ == '__main__':
    class Inherit(Base):
        def __init__(self, max=10):
            Base.__init__(self)
            self.base = "hoge"
            self.bin = numpy.arange(max)

    connect()
    print 'create inherit instance'
    inherit = Inherit()
    inherit.save()
    inherit2 = Inherit(3)
    inherit2.save()

    for inherit_ in Inherit.objects.all():
        print 'base: ', inherit_.base if 'base' in inherit_.__dict__ else None
        print 'bin: ', inherit_.bin if 'bin' in inherit_.__dict__ else None

    print "all task completed"
