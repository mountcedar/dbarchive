## はじめに

このパッケージは、クラスインスタンスとアトリビュートから自動的にテーブルを生成し、その内容をmongodbに保存するユーティリティを提供するパッケージです。
テーブルの作成を意識せず行うためのmongoengineの軽量ラッパーという位置付けで実装しています。

### 制限事項

* データベース操作スクリプトの欠如：現状、データベースやCollectionの削除はmongoコマンドで直に行う必要があります

## 動作環境

このパッケージはmongodbがローカルで動作している必要があります。まだ、インストールしていない場合はインストールしてください。

### OSXの場合

Homebrewを使ってインストールできます。

```
$ brew update
$ brew install mongodb
$ ln -sfv /usr/local/opt/mongodb/*.plist ~/Library/LaunchAgents
$ launchctl load ~/Library/LaunchAgents/homebrew.mxcl.mongodb.plist
```

### Ubuntuの場合

aptリポジトリにmongodb.orgを加えることでインストールできます。

```
$ sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
$ echo "deb http://repo.mongodb.org/apt/ubuntu "$(lsb_release -sc)"/mongodb-org/3.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.0.list
$ sudo apt-get update
$ sudo apt-get install -y mongodb-org
```

## インストール

pipを使ってインストールするのが便利です。

```
$ pip install git+https://github.com/mountcedar/dbarchive.git
```

master版ではなく、個々に発行された開発版のtarballや、developブランチをインストールする場合は、ソースをcloneした上でsetup.pyを用いてインストールします。

```
$ tar xzf dbarchive-X.X.X.tar.gz
$ cd dbarchive-X.X.X
## もしくは
$ git clone https://github.com/mountcedar/dbarchive.git
$ cd dbarchive
## ここからは共通
$ python ./setup.py install
```

### 用いるPythonディストリビューションの選択

インストールの際にsudoを書いていないのはユーザローカルにインストールされたpythonの使用を前提としているためです。システムのpythonを使用する場合は、sudoでインストールしてください。numpyなどの基本となるパッケージインストールでエラーが起きることを避けるためにpyenvなどを用いてユーザローカルのAnacondaなどのpython環境を構築することをおすすめします。

* [pyenvを用いたanacondaのインストール](http://qiita.com/yuichy/items/8cd43a667fb4659d89e9)

## アンインストール

pipを使ってアンインストールするのが便利です。

```
$ pip uninstall dbarchive
```

## 使い方

### Getting Started

サンプルコードは以下のとおりです。

```python
import numpy
import logging
from datetime import datetime
from dbarchive import Base

class Sample(Base):
    def __init__(self, maxval=10):
        self.base = "hoge"
        self.bin = numpy.arange(maxval)
        self.created = datetime.now()

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
```

上記のコードを簡単に解説します。
まず、データベースで管理したいクラスに、dbarchive.Baseクラスを継承させます。

```python
class Sample(Base):
    def __init__(self, maxval=10):
        self.base = "hoge"
        self.bin = numpy.arange(maxval)
        self.created = datetime.now()
```

dbarchive.Baseクラスを継承することで、データベース保存に必要なユーティリティを持ったクラスを作ることができます。
あとは、インスタンスをsave関数で保存するだけです。

なお、Baseクラスを継承するクラスの__init__メソッドは、引数なしで実行できるように設計されていないといけません。
これは、データベースからインスタンスを自動作成するときに引数なしでインスタンス化できる必要があるためです。

```python
print 'create sample instance'
sample01 = Sample(10)
sample01.save()
sample02 = Sample(3)
sample02.save()
```

save関数が呼び出されると、クラスは\<class名>\_tableというテーブル(collection)をデータベース内に作成してその値を格納します。

検索はクラスが持つobjectsというハンドラを通じて行います。objectsを通じたクエリの発行は基本的にdjango準拠の仕様になっているため、慣れている人にとってはとても使いやすいでしょう。


```python
for sample in Sample.objects.all():
    print 'sample: ', type(sample)
    print '\tbase: ', sample.base
    print '\tbin: ', sample.bin
    print '\tcreated: ', sample.created
```

上記は、これまで保存した全てのインスタンスを取得し、表示するコードです。objectsハンドラによるクエリセットの作成の詳細については以下のドキュメントを参考にしてください。

* [MongoEngine -- 2.5. Querying the database](http://docs.mongoengine.org/guide/querying.html)

## Tips

### mongodbへの格納

「はじめに」で書いたとおりこのパッケージはmongoengineの軽量ラッパーです。全てのクラスインスタンスは、ローカルのmongodbに格納されます。
デフォルトのデータベース名は

```
__py_dbarchive
```

という名前になっています。このデータベースにクラスごとに

```
<クラス名>_table
```

というテーブルを作成し、データを管理しています。この法則さえわかっていれば、mongoコマンドを使って、中身を直に確認することが可能です。例えば、サンプルコードのsampleクラスの内容を確認するには以下のようなコマンドを叩くと良いでしょう。

```bash
$ mongo
MongoDB shell version: 3.2.0
connecting to: test
> show dbs
__py_dbarchive  0.000GB
local           0.000GB
> use __py_dbarchive
switched to db __py_dbarchive
> db.sample_table.find()
{ "_id" : ObjectId("5688cd057fda359ffb66e59b"), "base" : "hoge", "bin" : BinData(0,"k05VTVBZAQBGAHsnZGVzY3InOiAnPGk4JywgJ2ZvcnRyYW5fb3JkZXInOiBGYWxzZSwgJ3NoYXBlJzogKDEwLCksIH0gICAgICAgICAgIAoAAAAAAAAAAAEAAAAAAAAAAgAAAAAAAAADAAAAAAAAAAQAAAAAAAAABQAAAAAAAAAGAAAAAAAAAAcAAAAAAAAACAAAAAAAAAAJAAAAAAAAAA=="), "archivers" : { "bin" : "NpyArchiver" } }
```

## バイナリデータの保持方法

mongodbの仕様でオブジェクト一つの容量に16Mの制限が加えられています。大容量のデータを扱う場合これでは足りなくなるため、GridFSと呼ばれる仕組みを使ってバイナリをチャンクに分けて保存します。そのため、変数のバイナリサイズ次第で動的生成されるテーブル構造が以下のように変化します。

* バイナリサイズが16Mbyte未満の場合：mongoengine.fields.BinaryFieldとして保存される
* バイナリサイズが16Mbyte以上の場合：LargeBinaryというテーブルのエントリを新規に作成し、そのテーブルのmongo.fields.FileFieldフィールドにバイナリが保存されます。そして、保存したLargeBinryエントリとの関係が保存されます。

使用しているデータベースに自分が定義されないCollectionが確認される場合、それらのCollectionは上記の大容量のバイナリ保存のために使用されています。

```
$ mongo
MongoDB shell version: 3.2.0
connecting to: test
> use __py_dbarchive
switched to db __py_dbarchive
> show collections
fs.chunks
fs.files
large_binary
m_l_p_table
sample_table
```

上記は、サンプルコードを実行した時のCollectionのリストを表示しています。自分で定義したクラス相当のテーブル以外にfs.chunks, fs.files, large_binaryなどのユーティリティのためのCollectionが作成されていることがわかります。

## 複数のユーザや複数のサーバで使用する場合のポイント

計算機サーバなどで、複数のユーザと並行してdbarchiveを使用する場合、デフォルトの使い方をすると同じデータベースを使うため、それぞれの実行結果が混ざって保存されることになります。その場合、connect関数を明示的に呼び出しデータベース名を指定することで別々のデータベースに結果を保存することが可能になります。

```python
from dbarchive import connect

...
connect('myown')
```

データベース名を指定することでその後のクラスが保存するデータベースを指定することが可能です。ちなみにconnect関数のパラメータはmongoengine.connect関数と互換性があるため、host, port, username, passwordなどの指定をすることも可能です。

```python
connect('myown', host="somedomain.com", port=12345)
connect('myown', host="somedomain.com", port=12345, username="hoge", password="geho")
```

複数のマシンで分散して学習した結果をデータベースに集約したい場合に使うと便利です。

### Collection旧定義の削除

drop_collection関数は対応するデータベースCollectionを削除するコマンドです。クラスの内容を再定義した場合などは、旧定義のものと整合が合わなくなることがあるので、この関数を使って、旧定義のCollectionを削除しましょう。

```
print 'dropping past sample collection'
Sample.drop_collection()
```

### より実用的な応用例

より実用的な応用例として、深層学習のパラメータセットを保存するサンプルコードを簡単に提供します。なお、全てのコードを書くと追い切れないので、gistsに置いたサンプルコードをダウンロードしながら、要点だけを説明します。使用したオリジナルのコードは以下のgithubプロジェクトから取得できます。

* https://github.com/hogefugabar/deep-learning-chainer

このパッケージは深層学習を行うためにchainerパッケージを使用します。まだインストールしていない人はpipでインストールしましょう。その後、サンプルをwgetで取得します。以下、取得したmlp.pyのオリジナルとの差分を抜粋しながら、dbarchiveの使い方を紹介します。

```
$ pip install chainer
$ wget https://gist.githubusercontent.com/mountcedar/be58ebfe1e9c752a72ac/raw/3e5dfb56cb471982b482bb0d536768ec2d52b21a/mlp.py
```

まず、このdbarchive.Baseクラスを継承します。このMLPクラスではxp変数としてモジュールを代入するというちょっと特殊な実装をしており、テーブルの作成に影響をあたえるため、excludes変数に入れて除外しておきます。

```python
from dbarchive import Base

...

class MLP(Base):
    def __init__(self, data, target, n_inputs=784, n_hidden=784, n_outputs=10, gpu=-1):
        self.excludes.append('xp')
...
```

あとは、学習が終わった時点でのmlpオブジェクトをsave関数で保存します。

```python
if __name__ == '__main__':
    ...
    mlp = MLP(data=data, target=target, gpu=args.gpu)
    mlp.train_and_test(n_epoch=1)
    mlp.save()
```

たった2箇所の操作を追加するだけで、学習済みのパラメータを簡単にデータベースに保存することができました。

```python
     for mlp_ in MLP.objects.all():
        print 'mlp: ', type(mlp_)
        for k, v in mlp.__dict__.items():
            if k.startswith('_'):
                continue
            print '\t{}: {}'.format(k, type(v))
```

クエリセットで保存したmlpオブジェクトの変数を表示してみると、しっかりと各変数が取得できていることがわかります。以下がサンプルコードの実行例です。

その後、取得したmlpオブジェクトを使って、再度、学習を行います。

```python
    print 'try learning again'
    mlp.train_and_test(n_epoch=1)
```

以下が実行結果です。識別率が上昇しており、確かに過去の学習結果が反映されていることがわかります。

```
$ python ./mlp.py 
dropping previously defined collection
fetch MNIST dataset
Not using gpu device
epoch 1
train mean loss=0.309873049351, accuracy=0.903980953055
test mean loss=0.129567001387, accuracy=0.95988571746
DEBUG:root:set attribute default: gpu, <type 'int'>
DEBUG:root:set attribute default: n_test, <type 'int'>
DEBUG:root:set attribute default: n_train, <type 'int'>
time = 1.05201875369 min
mlp:  <class '__main__.MLP'>
    x_test: <type 'numpy.ndarray'>
    x_train: <type 'numpy.ndarray'>
    default_archiver: <class 'dbarchive.base.PickleArchiver'>
    n_train: <type 'int'>
    collection: <class 'mongoengine.base.metaclasses.MLPTable'>
    n_test: <type 'int'>
    archivers: <type 'dict'>
    gpu: <type 'int'>
    xp: <type 'module'>
    optimizer: <class 'chainer.optimizers.adam.Adam'>
    model: <class 'chainer.function_set.FunctionSet'>
    y_test: <type 'numpy.ndarray'>
    y_train: <type 'numpy.ndarray'>
try learning again
epoch 1
train mean loss=0.146616529152, accuracy=0.953600001335
test mean loss=0.106004985619, accuracy=0.968000005313
```