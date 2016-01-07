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
from copy import deepcopy

import numpy
import pymongo
import mongoengine
# from mongoengine.document import Document
from mongoengine.document import DynamicDocument
from mongoengine import fields
from bson import Binary

__connected = False


def connect(database="__py_dbarchive", *args, **kwargs):
    '''
    the api to connect your local mongodb (by default host="localhost", port=27017).

    arguments are corresponding to the mongoengine api, mongoengine.connect
    see http://docs.mongoengine.org/apireference.html#mongoengine.connect
    '''
    global __connected
    try:
        if not __connected:
            con = pymongo.MongoClient(*args, **kwargs)
            con[database]
            del con
            mongoengine.connect(database, *args, **kwargs)
            __connected = True
    except:
        logging.error('connection to the mongodb failed.')


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
                entry.binary.put(bio, content_type="application/octet-stream")
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
                bin = obj.binary.read()
                logging.debug('bin: {}, size: {}'.format(type(bin), obj.binary.length))
                return f(self, Binary(bin))
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
    valid_classes = [int, float, long, bool, str, list, tuple, dict, datetime]
    default_excludes = [
        'valid_classes', 'default_excludes', 'default_archiver',
        'excludes', 'archivers', 'objects', 'collection'
    ]
    default_archiver = PickleArchiver()

    def __new__(cls, *args, **kwargs):
        connect()
        instance = super(Base, cls).__new__(cls)
        instance.excludes = deepcopy(cls.default_excludes)
        instance.archivers = {numpy.ndarray: NpyArchiver()}
        instance.collection = None
        return instance

    @classmethod
    def database(cls, obj=None):
        '''
        Dynamically define a child class of DynamicDocument based on the current class variable configuration.
        '''
        def getattribute(self, key):
            '''
            custom development of __getattribute__ for the DynamicDocument
            to directly convert the bson.Binary object into the specific type.
            '''
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

        def new(clazz, *args, **kwargs):
            '''
            custom development of __new__ for DynamicDocument.

            returns the class instance inheritating the Base class
            '''
            instance = super(DynamicDocument, clazz).__new__(clazz, *args, **kwargs)
            instance.__init__(*args, **kwargs)
            members = inspect.getmembers(instance, lambda a: not(inspect.isroutine(a)))
            attributes = [(k, v) for k, v in members if not k.startswith('_')]
            wrapper_instance = cls.__new__(cls)
            wrapper_instance.__init__()
            wrapper_instance.collection = instance
            for k, v in attributes:
                if isinstance(v, LargeBinary):
                    if k in instance.archivers:
                        archiver = eval(instance.archivers[k])()
                        logging.debug('variable: {} type {} is restored by {}'.format(k, type(v), archiver.__class__.__name__))
                        v = archiver.restore(v)
                wrapper_instance.__setattr__(k, v)
            return wrapper_instance

        attributes = {}
        if obj is None:
            attributes['__getattribute__'] = getattribute
            attributes['__new__'] = new
        return type(
            cls.__name__ + "Table",
            (DynamicDocument, ),
            attributes
        )

    def create_collection(self):
        '''
        create mongodb collection ORM based on the current class variable configuration
        '''
        collection = self.database(self)()
        members = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
        attributes = [(k, v) for k, v in members if not k.startswith('_')]
        archivers = {}
        for k, v in attributes:
            if k in self.excludes:
                continue
            if type(v) in self.valid_classes:
                logging.debug("set attribute default: {}, {}".format(k, type(v)))
                collection.__setattr__(k, v)
            elif type(v) in self.archivers.keys():
                logging.debug("set attribute customly binalized: {}, {}".format(k, type(v)))
                archiver = self.archivers[type(v)]
                archivers[k] = archiver.__class__.__name__
                binary = archiver.dump(v)
                collection.__setattr__(k, binary)
            else:
                logging.debug("set attribute pickled: {}, {}".format(k, type(v)))
                archivers[k] = self.default_archiver.__class__.__name__
                binary = self.default_archiver.dump(v)
                collection.__setattr__(k, binary)
        collection.__setattr__('archivers', archivers)
        return collection

    def save(self):
        '''
        Create a collection of the current class variables and save the current status in the mongodb.
        '''
        if self.collection is None:
            self.collection = self.create_collection()
        else:
            members = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
            attributes = [(k, v) for k, v in members if not k.startswith('_')]
            archivers = {}
            for k, v in attributes:
                if k in self.excludes:
                    continue
                if type(v) in self.valid_classes:
                    logging.debug("set attribute default: {}, {}".format(k, type(v)))
                    self.collection.__setattr__(k, v)
                elif type(v) in self.archivers.keys():
                    logging.debug("set attribute customly binalized: {}, {}".format(k, type(v)))
                    archiver = self.archivers[type(v)]
                    archivers[k] = archiver.__class__.__name__
                    binary = archiver.dump(v)
                    self.collection.__setattr__(k, binary)
                else:
                    logging.debug("set attribute pickled: {}, {}".format(k, type(v)))
                    archivers[k] = self.default_archiver.__class__.__name__
                    binary = self.default_archiver.dump(v)
                    self.collection.__setattr__(k, binary)
            self.collection.__setattr__('archivers', archivers)
        self.collection.save()

    @classmethod
    def drop_collection(cls):
        '''
        drop collection representing the class from mongodb
        '''
        connect()
        cls.database().drop_collection()

    class __metaclass__(type):
        @property
        def objects(cls):
            '''
            The queryset instance for quering the mongodb.
            '''
            connect()
            return cls.database().objects


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
