#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This source code is using chainer package to learn classifier of MNIST datasets with MLP.
The basic code is aquire from the github project

* https://github.com/hogefugabar/deep-learning-chainer

as

$ wget https://raw.githubusercontent.com/hogefugabar/deep-learning-chainer/master/mlp.py

After acquiring the basic code, we additionally refactor code for the dbarchive demonstration.
The usage detail of dbarchive can be read in

* https://github.com/mountcedar/dbarchive

----
2016/01/07
Osamu Sugiyama, https://github.com/mountcedar
'''

from dbarchive import Base
from dbarchive.base import LargeBinary
import argparse
import time
import numpy as np
from sklearn.datasets import fetch_mldata
from sklearn.cross_validation import train_test_split
from chainer import cuda, Variable, FunctionSet, optimizers
import chainer.functions as F


class MLP(Base):
    def __init__(self, data=None, target=None, n_inputs=784, n_hidden=784, n_outputs=10, gpu=-1):
        self.excludes.append('xp')
        self.model = FunctionSet(l1=F.Linear(n_inputs, n_hidden),
                                 l2=F.Linear(n_hidden, n_hidden),
                                 l3=F.Linear(n_hidden, n_outputs))

        if gpu >= 0:
            self.model.to_gpu()
            self.xp = cuda.cupy
        else:
            self.xp = np

        if not data is None:
            self.x_train, self.x_test = data
        else:
            self.x_train, self.y_test = None, None

        if not target is None:
            self.y_train, self.y_test = target
            self.n_train = len(self.y_train)
            self.n_test = len(self.y_test)
        else:
            self.y_train, self.y_test = None, None
            self.n_train = 0
            self.n_test = 0

        self.gpu = gpu
        self.optimizer = optimizers.Adam()
        self.optimizer.setup(self.model)

    def forward(self, x_data, y_data, train=True):
        x, t = Variable(x_data), Variable(y_data)
        h1 = F.dropout(F.relu(self.model.l1(x)), train=train)
        h2 = F.dropout(F.relu(self.model.l2(h1)), train=train)
        y = self.model.l3(h2)
        return F.softmax_cross_entropy(y, t), F.accuracy(y, t)

    def train_and_test(self, n_epoch=20, batchsize=100):
        for epoch in xrange(1, n_epoch+1):
            print 'epoch', epoch

            perm = np.random.permutation(self.n_train)
            sum_accuracy = 0
            sum_loss = 0
            for i in xrange(0, self.n_train, batchsize):
                x_batch = self.xp.asarray(self.x_train[perm[i:i+batchsize]])
                y_batch = self.xp.asarray(self.y_train[perm[i:i+batchsize]])

                real_batchsize = len(x_batch)

                self.optimizer.zero_grads()
                loss, acc = self.forward(x_batch, y_batch)
                loss.backward()
                self.optimizer.update()

                sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize
                sum_accuracy += float(cuda.to_cpu(acc.data)) * real_batchsize

            print 'train mean loss={}, accuracy={}'.format(sum_loss/self.n_train, sum_accuracy/self.n_train)

            # evalation
            sum_accuracy = 0
            sum_loss = 0
            for i in xrange(0, self.n_test, batchsize):
                x_batch = self.xp.asarray(self.x_test[i:i+batchsize])
                y_batch = self.xp.asarray(self.y_test[i:i+batchsize])

                real_batchsize = len(x_batch)

                loss, acc = self.forward(x_batch, y_batch, train=False)

                sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize
                sum_accuracy += float(cuda.to_cpu(acc.data)) * real_batchsize

            print 'test mean loss={}, accuracy={}'.format(sum_loss/self.n_test, sum_accuracy/self.n_test)


if __name__ == '__main__':
    import logging
    import cPickle as pickle

    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='MNIST')
    parser.add_argument('--gpu', '-g', default=-1, type=int,
                        help='GPU ID (negative value indicates CPU)')
    args = parser.parse_args()

    print 'dropping previously defined collection'
    MLP.drop_collection()

    print 'fetch MNIST dataset'
    mnist = fetch_mldata('MNIST original')
    mnist.data = mnist.data.astype(np.float32)
    mnist.data /= 255
    mnist.target = mnist.target.astype(np.int32)
    data_train, data_test, target_train, target_test = train_test_split(mnist.data, mnist.target)

    data = [data_train, data_test]
    target = [target_train, target_test]

    start_time = time.time()

    if args.gpu >= 0:
        cuda.check_cuda_available()
        cuda.get_device(args.gpu).use()
        print "Using gpu device 0: GeForce GT 620"
    else:
        print "Not using gpu device"

    mlp = MLP(data=data, target=target, gpu=args.gpu)
    mlp.train_and_test(n_epoch=1)
    mlp.save()
    end_time = time.time()

    with open('xtrain.pkl', 'wb') as fp:
        pickle.dump(mlp.x_train, fp)

    print "time = {} min".format((end_time-start_time)/60.0)

    for mlp_ in MLP.objects.all():
        print 'mlp: ', type(mlp_)
        print '\tmodel: ', type(mlp_.model)
        print '\tx_train: ', type(mlp_.x_train) if not isinstance(mlp_.x_train, LargeBinary) else mlp_.x_train
        if isinstance(mlp_.x_train, LargeBinary):
            print 'x_train pk: ', mlp_.x_train.pk
        print '\tx_test: ', type(mlp_.x_test) if not isinstance(mlp_.x_test, LargeBinary) else mlp_.x_test
        if isinstance(mlp_.x_test, LargeBinary):
            print 'x_test pk: ', mlp_.x_test.pk
        print '\ty_train: ', type(mlp_.y_train) if not isinstance(mlp_.y_train, LargeBinary) else mlp_.y_train
        print '\ty_test: ', type(mlp_.y_test) if not isinstance(mlp_.y_test, LargeBinary) else mlp_.y_test
        print '\toptimizer: ', type(mlp_.optimizer) if not isinstance(mlp_.optimizer, LargeBinary) else mlp_.optimizer

    # print 'try learning again.'
    # print mlp.__dict__
    # mlp.train_and_test()
