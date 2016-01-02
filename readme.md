# はじめに

このパッケージは、クラスインスタンスとアトリビュートから自動的にテーブルを生成し、その内容を保存するユーティリティを提供するパッケージです。

## インストール

pipを使ってインストールするのが便利です。

```
$ pip install 
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

ソフトウェアのハンドラであるhandle.pyを使って、各種機能を実行します。詳細はhelpオプションを試用してご確認ください。
