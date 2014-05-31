#!/usr/bin/python2

from __future__ import with_statement, print_function

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations

from utils import *

# ufspath('foo') = 'foo/.ufs'
# ufspath('foo', 'bar/baz' = 'foo/.ufs/bar/baz'
def ufspath(root, path=None):
    if path is None:
        return root + '/.ufs'
    return root + '/.ufs/' + path

# Validate that all paths are directories, contain a .ufs
# directory, and have the same directory contents.
def validateRootDirs(directories):
    if not directories:
        return

    dicts = []

    for directory in directories:
        if not os.path.isdir(directory):
            error(directory + ' is not a directory')
        if '.ufs' not in os.listdir(directory):
            error(directory + ' does not contain .ufs/')
        ufsdir = ufspath(directory)
        dicts.append((ufsdir, directory_dict(ufsdir)))

    firstDict = dicts[0]
    for otherDict in dicts[1:]:
        if not firstDict[1] == otherDict[1]:
            error("directory tree mismatch: %s, %s" % (firstDict[0], otherDict[0]))

class UnifiedCloudStorage(Operations):
    def __init__(self, mountpoint, roots):
        self.roots = roots
        validateRootDirs(roots)

        def on_file(filename):
            # xor all files together
            contents = open(ufspath(roots[0], filename), 'r').read()
            print('contents before xor: ' + contents)
            for next_root in roots[1:]:
                with open(ufspath(next_root, filename)) as handle:
                    next_contents = handle.read()

                    if len(contents) != len(next_contents):
                        error('Corrupt data: len(%s) != len (%s) (%d != %d)'
                                % (ufspath(roots[0], filename),
                                    ufspath(next_root, filename),
                                    len(contents),
                                    len(next_contents)))

                    contents = xor_strings(contents, next_contents)
                    print('contents after xor: ' + contents)

            with open(mountpoint + '/' + filename, 'w') as dest:
                dest.write(contents)
            print('wrote file: ' + filename)

        def on_dir(dirname):
            os.mkdir(mountpoint + '/' + dirname)
            print('made dir: ' + dirname)

        traverse(ufspath(roots[0]), on_file, on_dir)

    # Helpers
    # =======

    def getPaths(self, relative):
        for rootDir in self.config.rootDirs:
            yield os.path.join(rootDir, relative)

    # Filesystem methods
    # ==================

    def create(self, path, mode, fi=None):
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in
            ( 'st_atime'
            , 'st_ctime'
            , 'st_gid'
            , 'st_mode'
            , 'st_mtime'
            , 'st_nlink'
            , 'st_size'
            , 'st_uid'
            ))

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in
            ( 'f_bavail'
            , 'f_bfree'
            , 'f_blocks'
            , 'f_bsize'
            , 'f_favail'
            , 'f_ffree'
            , 'f_files'
            , 'f_flag'
            , 'f_frsize'
            , 'f_namemax'
            ))


    def unlink(self, path):
        return os.unlink(self._full_path(path))

    def symlink(self, target, name):
        return os.symlink(self._full_path(target), self._full_path(name))

    def rename(self, old, new):
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fg)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fg):
        return self.flush(path, fh)

def error(*objs):
    print("ERROR: ", *objs, file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        error('Usage: %s <mountpoint> [<sub-filesystems>]' % sys.argv[0])

    if os.listdir(sys.argv[1]):
        error('Mountpoint must be empty.')

    FUSE(
        UnifiedCloudStorage(sys.argv[1], sys.argv[2:]),
        sys.argv[1],
        foreground=True)
