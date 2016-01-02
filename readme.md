# はじめに

このパッケージは、クラスインスタンスとアトリビュートから自動的にテーブルを生成し、その内容を保存するユーティリティを提供するパッケージです。

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

サンプルコードは以下のとおりです。

```sample.py
import numpy
from dbarchive import connect
from dbarchive import Base

class Inherit(Base):
    def __init__(self, max=10):
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
