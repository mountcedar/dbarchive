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
import traceback
from copy import deepcopy
import hashlib
from functools import partial

import numpy
import pymongo
import mongoengine
# from mongoengine.document import Document
from mongoengine.document import DynamicDocument
from mongoengine import fields
# from bson import Binary

__connection = None


def connect(database="__py_dbarchive", *args, **kwargs):
    '''
    the api to connect your local mongodb (by default host="localhost", port=27017).

    arguments are corresponding to the mongoengine api, mongoengine.connect
    see http://docs.mongoengine.org/apireference.html#mongoengine.connect
    '''
    global __connection
    try:
        if __connection is None:
            __connection = pymongo.MongoClient(*args, **kwargs)
            __connection[database]
            mongoengine.connect(database, *args, **kwargs)
        return __connection
    except:
        logging.error('connection to the mongodb failed.')
        return None


def drop_database(database="__py_dbarchive", *args, **kwargs):
    try:
        con = connect(database, *args, **kwargs)
        con.drop_database(database)
    except:
        logging.error()


def md5sum(f):
    '''
    returns md5sum of file-like object
    '''
    d = hashlib.md5()
    for buf in iter(partial(f.read, 128), b''):
        d.update(buf)
    return d.hexdigest()


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
    parents = fields.ListField(fields.ObjectIdField())
    variable = fields.StringField(default=None)
    archiver = fields.StringField(default=None)
    binary = fields.FileField(default=None)
    md5sum = fields.StringField(default=None)
    updated = fields.DateTimeField(default=None)


class Archiver(object):
    '''
    the superclass for archiving the mogoengine unsupporting variables in the class.

    The child class of this class should have dump / restore methods
    for handling the binary expression of the variable.

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

            for binary in LargeBinary.objects.filter(parents_contains=instance.pk).all():
                logging.debug('key {}: {}'.format(binary.variable, binary.pk))
                logging.debug('archive: {}'.format(binary.archiver))
                archiver = eval(binary.archiver)()
                binary.binary.seek(0)
                obj = archiver.restore(binary.binary)
                wrapper_instance.__setattr__(binary.variable, obj)

            return wrapper_instance

        attributes = {}
        if custom:
            attributes['__new__'] = new
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
            fp = None
            md5sum_ = 0
            archiver = None

            if type(v) in self.archivers:
                archiver = self.archivers[type(v)]
                fp = archiver.dump(v)
                fp.seek(0)
                md5sum_ = md5sum(fp)
            else:
                archiver = self.default_archiver
                fp = archiver.dump(v)
                fp.seek(0)
                md5sum_ = md5sum(fp)

            filtered = LargeBinary.objects(
                md5sum=md5sum_, variable=k
            )

            if filtered:
                old_md5sum = filtered.first().md5sum
            else:
                old_md5sum = None

            binary = filtered.modify(
                upsert=True, new=True,
                add_to_set__parents=self.collection.pk,
                set__variable=k
            )

            # if binary.md5sum == md5sum_:
            #     logging.debug('same object has already exists on the database for {}'.format(k))
            #     continue
            # else:
            #     logging.debug('different md5sum: binary>{}, created>{}'.format(binary.md5sum, md5sum_))

            if old_md5sum != md5sum_:
                '''
                FileField object is not automatically deleted.
                You must delete it expressly.

                See the details in

                * http://docs.mongoengine.org/guide/gridfs.html
                '''
                logging.debug('newly adding binary contents')
                fp.seek(0)
                binary.binary.delete()
                binary.binary.put(fp)
                # binary.md5sum = md5sum_
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

        @property
        def native_objects(cls):
            '''
            The queryset instance for quering the mongodb.
            '''
            connect()
            return cls.database(False).objects


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
