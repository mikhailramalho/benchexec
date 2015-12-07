#!/bin/bash

set -e

if [ -z "$1" ]; then
  echo "Please specify to-be-released version as parameter."
  exit 1
fi

OLD_VERSION="$(grep __version__ benchexec/__init__.py | sed -e "s/^.*'\(.*\)'.*$/\1/")"
VERSION="$1"
if [ $(expr match "$VERSION" ".*dev") -gt 0 ]; then
  echo "Cannot release development version."
  exit 1
fi
if [ "$VERSION" = "$OLD_VERSION" ]; then
  echo "Version already exists."
  exit 1
fi
if ! grep -q "BenchExec $VERSION" CHANGELOG.md; then
  echo "Cannot release version without changelog, please update CHANGELOG.md"
  exit 1
fi
if [ ! -z "$(git status -uno -s)" ]; then
  echo "Cannot release with local changes, please stash them."
  exit 1
fi

if [ -z "$DEBFULLNAME" ]; then
  echo "Please define environment variable DEBFULLNAME with your name you want to use for the Debian package."
  exit 1
fi
if [ -z "$DEBEMAIL" ]; then
  echo "Please define environment variable DEBEMAIL with your name you want to use for the Debian package."
  exit 1
fi
if ! which pandoc > /dev/null; then
  echo 'Please install pandoc, e.g. with "sudo apt-get install pandoc".'
  exit 1
fi
if ! which twine > /dev/null; then
  echo 'Please install twine, e.g. with "pip3 install --user twine".'
  exit 1
fi

# Prepare files with new version number
sed -e "s/^__version__ = .*/__version__ = '$VERSION'/" -i benchexec/__init__.py
dch -v "$VERSION-1" "New upstream version."
dch -r ""

git commit debian/changelog benchexec/__init__.py -m"Release $VERSION"


# Other preparations
DIR="$(pwd)"
DIST_DIR="$DIR/dist-$VERSION"
rm -r "$DIST_DIR" 2>/dev/null || true
mkdir "$DIST_DIR"


# Test and build under Python 3
TEMP3="$(mktemp -d)"
virtualenv -p /usr/bin/python3 --system-site-packages "$TEMP3"
. "$TEMP3/bin/activate"
git clone "file://$DIR" "$TEMP3/benchexec"
pushd "$TEMP3/benchexec"
pip install -e "."
pip install pypandoc
python setup.py nosetests
python setup.py sdist bdist_egg bdist_wheel
popd
deactivate
cp "$TEMP3/benchexec/dist/"* "$DIST_DIR"
rm -rf "$TEMP3"

# Test and build under Python 2
TEMP2="$(mktemp -d)"
virtualenv -p /usr/bin/python2 "$TEMP2"
. "$TEMP2/bin/activate"
git clone "file://$DIR" "$TEMP2/benchexec"
pushd "$TEMP2/benchexec"
pip install -e "."
pip install pypandoc
python setup.py test
python setup.py bdist_egg
popd
deactivate
cp "$TEMP2/benchexec/dist/"* "$DIST_DIR"
rm -rf "$TEMP2"


# Build Debian package
TAR="BenchExec-$VERSION.tar.gz"

TEMP_DEB="$(mktemp -d)"
cp "$DIST_DIR/$TAR" "$TEMP_DEB"
pushd "$TEMP_DEB"
tar xf "$TAR"
cp -r "$DIR/debian" "$TEMP_DEB/BenchExec-$VERSION"
cd "BenchExec-$VERSION"

dh_make -p "benchexec_$VERSION" --createorig -f "../$TAR" -i -c apache || true

dpkg-buildpackage -us -uc
popd
cp "$TEMP_DEB/benchexec_$VERSION-1_all.deb" "$DIST_DIR"
rm -rf "$TEMP_DEB"

for f in "$DIST_DIR/"*; do
  gpg --detach-sign -a "$f"
done
git tag -s "$VERSION" -m "Relase $VERSION"


# Upload and finish
read -p "Everything finished, do you want to release version '$VERSION' publically? (y/n) " -n 1 -r
echo
if ! [[ $REPLY =~ ^[Yy]$ ]]; then
  exit 0
fi

git push --tags
twine upload "$DIST_DIR/BenchExec"*

read -p "Please enter next version number:  " -r
sed -e "s/^__version__ = .*/__version__ = '$REPLY'/" -i benchexec/__init__.py
git commit benchexec/__init__.py -m"Prepare version number for next development cycle."


echo
echo "Please create a release on GitHub and add content from CHANGELOG.md and files from $DIST_DIR/:"
echo "https://github.com/sosy-lab/benchexec/releases"
