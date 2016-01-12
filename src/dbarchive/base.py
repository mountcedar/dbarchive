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
# import traceback
from copy import deepcopy

import numpy
import pymongo
import mongoengine
# from mongoengine.document import Document
from mongoengine.document import DynamicDocument
from mongoengine import fields
# from bson import Binary

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
    parent_id = fields.ObjectIdField()
    variable = fields.StringField()
    archiver = fields.StringField()
    binary = fields.FileField()
    updated = fields.DateTimeField(default=None)


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
        Accept any object as an argument and dump it into a file stream
        '''
        return None

    @abstractmethod
    def restore(self, obj):
        '''
        Accept file stream and restore it as a input variable style.
        '''
        return None


class PickleArchiver(Archiver):
    '''
    The Archiver implementation with pickle format.
    '''
    def dump(self, obj):
        bio = io.BytesIO()
        pickle.dump(obj, bio)
        return bio

    def restore(self, fp):
        return pickle.load(fp)


class NpyArchiver(Archiver):
    '''
    The Archiver implementation with npy format.
    '''
    def dump(self, obj):
        bio = io.BytesIO()
        numpy.save(bio, obj)
        return bio

    def restore(self, fp):
        return numpy.load(fp)


class Base(object):
    '''
    Base utility class to store its variables into the mongodb collection.
    '''
    valid_classes = [int, float, long, bool, str, list, tuple, dict, datetime]
    default_excludes = [
        'valid_classes', 'default_excludes', 'default_archiver',
        'excludes', 'archivers', 'objects', 'collection'
    ]
    excludes = []

    def __new__(cls, *args, **kwargs):
        connect()
        instance = super(Base, cls).__new__(cls)
        cls.excludes = deepcopy(cls.default_excludes)
        instance.default_archiver = PickleArchiver()
        instance.archivers = {numpy.ndarray: NpyArchiver()}
        instance.collection = None
        return instance

    @classmethod
    def database(cls, custom=True):
        '''
        Dynamically define a child class of DynamicDocument based on the current class variable configuration.
        '''
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
                if k in cls.excludes:
                    continue
                wrapper_instance.__setattr__(k, v)

            for binary in LargeBinary.objects.filter(parent_id=instance.pk).all():
                # logging.debug('binary: {}'.format(binary.pk))
                archiver = eval(binary.archiver)()
                obj = archiver.restore(binary.binary)
                wrapper_instance.__setattr__(binary.variable, obj)

            return wrapper_instance

        attributes = {}
        if custom:
            attributes['__new__'] = new
            pass
        return type(
            cls.__name__ + "Table",
            (DynamicDocument, ),
            attributes
        )

    def save(self):
        '''
        Create a collection of the current class variables and save the current status in the mongodb.
        '''
        if self.collection is None:
            self.collection = self.create_collection()
        else:
            members = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
            attributes = [(k, v) for k, v in members if not k.startswith('_')]
            # archivers = {}
            binaries = {}
            for k, v in attributes:
                if k in self.excludes:
                    continue
                if type(v) in self.valid_classes:
                    self.collection.__setattr__(k, v)
                else:
                    binaries[k] = v
            self.update_binaries(binaries)
            # self.collection.__setattr__('archivers', archivers)
        self.collection.save()

    def create_collection(self):
        '''
        create mongodb collection ORM based on the current class variable configuration
        '''
        self.collection = self.database(custom=False)()
        members = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
        attributes = [(k, v) for k, v in members if not k.startswith('_')]
        # archivers = {}
        binaries = {}
        for k, v in attributes:
            if k in self.excludes:
                continue
            if type(v) in self.valid_classes:
                logging.debug("set attribute default: {}, {}".format(k, type(v)))
                self.collection.__setattr__(k, v)
            else:
                binaries[k] = v
        # self.collection.__setattr__('archivers', archivers)
        self.collection.save()
        self.update_binaries(binaries)
        return self.collection

    def update_binaries(self, binaries):
        for k, v in binaries.items():
            binary = LargeBinary.objects(
                parent_id=self.collection.pk, variable=k
            ).modify(
                upsert=True, new=True,
                set__parent_id=self.collection.pk,
                set_variable=k
            )
            if not binary.updated is None:
                '''
                FileField object is not automatically deleted.
                You must delete it expressly.

                See the details in

                * http://docs.mongoengine.org/guide/gridfs.html
                '''
                logging.debug('updaring binary')
                binary.binary.delete()

            if type(v) in self.archivers:
                archiver = self.archivers[type(v)]
                fp = archiver.dump(v)
                fp.seek(0)
                binary.binary.put(fp)
                binary.archiver = archiver.__class__.__name__
                binary.updated = datetime.now()
                binary.save()
            else:
                archiver = self.default_archiver
                fp = archiver.dump(v)
                fp.seek(0)
                binary.binary.put(fp)
                binary.archiver = archiver.__class__.__name__
                binary.updated = datetime.now()
                binary.save()

    @classmethod
    def drop_collection(cls):
        '''
        drop collection representing the class from mongodb
        '''
        connect()
        for obj in cls.database(custom=False).objects.all():
            for binary in LargeBinary.objects.filter(parent_id=obj.pk).all():
                binary.binary.delete()
                binary.delete()
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
