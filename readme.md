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
from dbarchive import connect
from dbarchive import Base

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
```

上記のコードを簡単に解説します。まず、データベースに接続します。

```
connect()
```

次に、データベースで管理したいクラスに、dbarchive.Baseクラスを継承させます。

```python
class Sample(Base):
    def __init__(self, max=10):
        Base.__init__(self)
        self.base = "hoge"
        self.bin = numpy.arange(max)
```

dbarchive.Baseクラスを継承することで、データベース保存に必要なユーティリティを持ったクラスを作ることができます。
あとは、インスタンスをsave関数で保存するだけです。

```python
print 'create inherit instance'
sample01 = Sample(max=10)
sample01.save()
sample02 = Sample(max=3)
sample02.save()
```

save関数が呼び出されると、クラスは\<class名>\_tableというテーブル(collection)をデータベース内に作成してその値を格納します。

検索はクラスが持つobjectsというハンドラを通じて行います。objectsを通じたクエリの発行は基本的にdjango準拠の仕様になっているため、慣れている人にとってはとても使いやすいでしょう。


```python
for sample in Sample.objects.all():
    print 'base: ', sample.base
    print 'bin: ', sample.bin
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
> db.inherit_table.find()
{ "_id" : ObjectId("5688cd057fda359ffb66e59b"), "base" : "hoge", "bin" : BinData(0,"k05VTVBZAQBGAHsnZGVzY3InOiAnPGk4JywgJ2ZvcnRyYW5fb3JkZXInOiBGYWxzZSwgJ3NoYXBlJzogKDEwLCksIH0gICAgICAgICAgIAoAAAAAAAAAAAEAAAAAAAAAAgAAAAAAAAADAAAAAAAAAAQAAAAAAAAABQAAAAAAAAAGAAAAAAAAAAcAAAAAAAAACAAAAAAAAAAJAAAAAAAAAA=="), "archivers" : { "bin" : "NpyArchiver" } }
```

## バイナリデータの保持方法

mongodbの仕様で一つのオブジェクト一つの容量に16Mの制限が加えられています。大容量のデータを扱う場合これでは足りなくなるため、GridFSと呼ばれる仕組みを使ってバイナリをチャンクに分けて保存します。そのため、変数のバイナリサイズ次第で動的生成されるテーブル構造が以下のように変化します。

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

計算機サーバなどで、複数のユーザと並行してdbarchiveを使用する場合、デフォルトの使い方をすると同じデータベースを使うため、それぞれの実行結果が混ざって保存されることになります。その場合、connect関数にデータベース名を指定することで別々のデータベースに結果を保存することが可能になります。

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
from dbarchive import connect

...

class MLP(Base):
    def __init__(self, data, target, n_inputs=784, n_hidden=784, n_outputs=10, gpu=-1):
        Base.__init__(self)
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
        print 'mlp model: ', type(mlp_.model)
```

クエリセットで保存したmodel変数を表示してみると、しっかりとFunctionSetが取得できていることがわかります。以下がサンプルコードの実行例です。

```
$ python ./mlp.py 
connecting to mongodb
fetch MNIST dataset
Not using gpu device
epoch 1
train mean loss=0.309678050698, accuracy=0.904990477392
test mean loss=0.125952891005, accuracy=0.962742861339
time = 0.479408101241 min
mlp model:  <class 'chainer.function_set.FunctionSet'>
```