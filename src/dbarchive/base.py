#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Base module for implementing the abstract class for ORM
'''

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
# from mongoengine.document import Document
from mongoengine.document import DynamicDocument
from mongoengine import fields
from bson import Binary


def connect(database="__py_dbarchive", *args, **kwargs):
    '''
    the api to connect your local mongodb (by default host="localhost", port=27017).

    arguments are corresponding to the mongoengine api, mongoengine.connect
    see http://docs.mongoengine.org/apireference.html#mongoengine.connect
    '''
    con = pymongo.MongoClient(*args, **kwargs)
    con[database]
    del con
    mongoengine.connect(database, *args, **kwargs)


class LargeBinary(DynamicDocument):
    '''
    The ORM model for large binary.

    Since the mongodb restrict each object size exceed to 16MB.
    The binary beyond 16MB should be stored using the GridFS feature.
    This table model is for dealing with the binary larger than 16MB,
    using the FileField in mongoengine.

    The detail description concerning the GridFS can be found in

    - GridFS supports in mongoengine: http://docs.mongoengine.org/guide/gridfs.html
    - GridFS: https://docs.mongodb.org/manual/core/gridfs/
    '''
    binary = fields.FileField()
    created = fields.DateTimeField()


class Archiver(object):
    '''
    the superclass for archiving the mogoengine unsupporting variables in the class.

    The child class of this class should have dump / restore methods
    for handling the binary expression of the variable.
    dump() method be also with post_dump decorator as well as
    restore() method be with pre_restore decorator.

    See PickleArchiver, NpyArchiver for more concrete example.
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def dump(self, obj):
        '''
        Accept any object as an argument and dump it into a bson.Binary expression.
        '''
        return None

    @abstractmethod
    def restore(self, obj):
        '''
        Accept bson.Binary expression and restore it as a input variable style.
        '''
        return None

    @classmethod
    def post_dump(cls, f):
        '''
        The definition of post-dump processing.

        if the object size exceed 16MB, then create a LargeBinary instance
        and hold it as a ReferenceFiled in the table.
        '''
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
        '''
        The definition of pre-restore processing.

        Accept LargeBinary reference and extract bson.Binary instance from it
        and pass the instance to the restore method
        '''
        def _filter(self, obj):
            if isinstance(obj, LargeBinary):
                logging.debug('large binary instance coming')
                return f(self, Binary(obj.binary.read()))
            else:
                return f(self, obj)
        return _filter


class PickleArchiver(Archiver):
    '''
    The Archiver implementation with pickle format.
    '''
    @Archiver.post_dump
    def dump(self, obj):
        bio = io.BytesIO()
        pickle.dump(obj, bio)
        return Binary(bio.getvalue())

    @Archiver.pre_restore
    def restore(self, obj):
        return pickle.load(io.BytesIO(obj))


class NpyArchiver(Archiver):
    '''
    The Archiver implementation with npy format.
    '''
    @Archiver.post_dump
    def dump(self, obj):
        bio = io.BytesIO()
        numpy.save(bio, obj)
        return Binary(bio.getvalue())

    @Archiver.pre_restore
    def restore(self, obj):
        return numpy.load(io.BytesIO(obj))


class Base(object):
    '''
    Base utility class to store its variables into the mongodb collection.
    '''
    valid_classes = [int, float, long, bool, str, list, tuple, dict]
    default_archiver = PickleArchiver()

    def __init__(self):
        self.excludes = ['valid_classes', 'default_archiver', 'excludes', 'archivers', 'objects']
        self.archivers = {numpy.ndarray: NpyArchiver()}

    @classmethod
    def database(cls, obj=None):
        '''
        Dynamically define a child class of DynamicDocument based on the current class variable configuration.
        '''
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
        '''
        Create a collection of the current class variables and save the current status in the mongodb.
        '''
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
            '''
            The queryset instance for quering the mongodb.
            '''
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
