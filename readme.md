# はじめに

このパッケージは、クラスインスタンスとアトリビュートから自動的にテーブルを生成し、その内容をmongodbに保存するユーティリティを提供するパッケージです。
テーブルの作成を意識せず行うためのmongoengineの軽量ラッパーという位置付けで実装しています。

_*なお、まだ実装中なため、ちゃんと動作しません。安定版のリリースまでしばらくお待ち下さい。*_

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
from dbarchive import connect
from dbarchive import Base

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
```

まず、データベースに接続します。

```
connect()
```

次に、データベースで管理したいクラスに、dbarchive.Baseクラスを継承させます。

```python
class Inherit(Base):
    def __init__(self, max=10):
        Base.__init__(self)
        self.base = "hoge"
        self.bin = numpy.arange(max)
```

dbarchive.Baseクラスを継承することで、データベース保存に必要なユーティリティを持ったクラスを作ることができます。
あとは、インスタンスをsave関数で保存するだけです。

```python
print 'create inherit instance'
inherit = Inherit()
inherit.save()
inherit2 = Inherit(3)
inherit2.save()
```

save関数が呼び出されると、クラスは\<class名>\_tableというテーブル(collection)をデータベース内に作成してその値を格納します。

検索はクラスが持つobjectsというハンドラを通じて行います。objectsを通じたクエリの発行は基本的にdjango準拠の仕様になっているため、慣れている人にとってはとても使いやすいでしょう。


```python
for inherit_ in Inherit.objects.all():
    print 'base: ', inherit_.base if 'base' in inherit_.__dict__ else None
    print 'bin: ', inherit_.bin if 'bin' in inherit_.__dict__ else None
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

というテーブルを作成し、データを管理しています。この法則さえわかっていれば、mongoコマンドを使って、中身を直に確認することが可能です。例えば、サンプルコードのinheritクラスの内容を確認するには以下のようなコマンドを叩くと良いでしょう。

```bash
 mongo
MongoDB shell version: 3.2.0
connecting to: test
> show dbs
__py_dbarchive  0.000GB
local           0.000GB
> use __py_dbarchive
switched to db __py_dbarchive
> db.inherit_table.find()
{ "_id" : ObjectId("5688cd057fda359ffb66e59b"), "base" : "hoge", "bin" : BinData(0,"k05VTVBZAQBGAHsnZGVzY3InOiAnPGk4JywgJ2ZvcnRyYW5fb3JkZXInOiBGYWxzZSwgJ3NoYXBlJzogKDEwLCksIH0gICAgICAgICAgIAoAAAAAAAAAAAEAAAAAAAAAAgAAAAAAAAADAAAAAAAAAAQAAAAAAAAABQAAAAAAAAAGAAAAAAAAAAcAAAAAAAAACAAAAAAAAAAJAAAAAAAAAA=="), "archivers" : { "bin" : "NpyArchiver" } }
```

