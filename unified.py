#!/usr/bin/python2

from __future__ import with_statement, print_function

import errno
import os
import shutil
import sys
import tempfile

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

    log('Validating directories...')
    for directory in directories:
        if not os.path.isdir(directory):
            error(directory + ' is not a directory')
        if '.ufs' not in os.listdir(directory):
            os.mkdir(os.path.join(directory, '.ufs'))
        ufsdir = ufspath(directory)
        dicts.append((ufsdir, directory_dict(ufsdir)))

    firstDict = dicts[0]
    for otherDict in dicts[1:]:
        if not firstDict[1] == otherDict[1]:
            error("directory tree mismatch: %s, %s" % (firstDict[0], otherDict[0]))

class UnifiedCloudStorage(Operations):
    def __init__(self, raidver, roots):
        if raidver == '--raid0':
            self.raid = 0
        elif raidver == '--raid4':
            self.raid = 4
        else:
            error('Unrecognized RAID flag: ' + raidver)

        self.root = tempfile.mkdtemp()
        self.roots = roots
        log('Created pass-through filesystem at ' + self.root)

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    ############################################################################

    def create(self, path, mode, fi=None):
        log('CREATE ' + path)
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def destroy(self, path):
        if self.raid == 0:
            self.destroy_raid0(path)
        elif self.raid == 4:
            self.destroy_raid4(path)
        else:
            error('NOT REACHED')

    def destroy_raid0(self, path):
        def on_file(root, filename):
            full_path = self._full_path(filename)
            contents = open(full_path, 'r').read()

            random_bits = []
            for directory in self.roots[1:]:
                ufs_path = ufspath(directory, filename)
                bits = os.urandom(len(contents))

                with open(ufs_path, 'w') as handle:
                    log('Writing ' + ufs_path)
                    handle.write(bits)

                random_bits.append(bits)

            ufs_path = ufspath(self.roots[0], filename)
            with open(ufs_path, 'w') as handle:
                log('Writing ' + ufs_path)
                handle.write(xor_strings(contents, *random_bits))

        def on_dir(dirname):
            for directory in self.roots:
                ufs_path = ufspath(directory, dirname)
                log('Making ' + ufs_path)
                os.mkdir(ufs_path)

        log('DESTROY ' + path)

        # Delete roots' files, re-build from scratch
        for directory in self.roots:
            ufs_path = ufspath(directory)
            log('Removing ' + ufs_path)
            shutil.rmtree(ufs_path)
            os.mkdir(ufs_path)

        traverse(self.root, on_file, on_dir)

    def destroy_raid4(self, path):
        return
        def on_file(root, filename):
            full_path = self._full_path(filename)
            contents = open(full_path, 'r').read()

            random_bits = []
            for directory in self.roots[1:]:
                ufs_path = ufspath(directory, filename)
                bits = os.urandom(len(contents))

                with open(ufs_path, 'w') as handle:
                    log('Writing ' + ufs_path)
                    handle.write(bits)

                random_bits.append(bits)

            ufs_path = ufspath(self.roots[0], filename)
            with open(ufs_path, 'w') as handle:
                log('Writing ' + ufs_path)
                handle.write(xor_strings(contents, *random_bits))

        def on_dir(dirname):
            for directory in self.roots:
                ufs_path = ufspath(directory, dirname)
                log('Making ' + ufs_path)
                os.mkdir(ufs_path)

        # Delete roots' files, re-build from scratch
        for directory in self.roots:
            ufs_path = ufspath(directory)
            log('Removing ' + ufs_path)
            shutil.rmtree(ufs_path)
            os.mkdir(ufs_path)

        traverse(self.root, on_file, on_dir)

    def flush(self, path, fh):
        log('FLUSH ' + path)
        return os.fsync(fh)

    def fsync(self, path, fdatasync, fh):
        log('FSYNC ' + path)
        return self.flush(path, fh)

    def getattr(self, path, fh=None):
        log('GETATTR ' + path)
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

    def init(self, path):
        if self.raid == 0:
            self.init_raid0(path)
        elif self.raid == 4:
            self.init_raid4(path)
        else:
            error('NOT REACHED')

    def init_raid0(self, path):
        def on_file(root, filename):
            # xor all files together
            contents = open(ufspath(self.roots[0], filename), 'r').read()
            for next_root in self.roots[1:]:
                with open(ufspath(next_root, filename), 'r') as handle:
                    next_contents = handle.read()

                    if len(contents) != len(next_contents):
                        error('Corrupt data: len(%s) != len (%s) (%d != %d)'
                                % (ufspath(self.roots[0], filename),
                                    ufspath(next_root, filename),
                                    len(contents),
                                    len(next_contents)))

                    contents = xor_strings(contents, next_contents)

            full_path = self._full_path(filename)
            with open(full_path, 'w') as dest:
                dest.write(contents)

            log('Wrote ' + full_path)

        def on_dir(dirname):
            full_path = self._full_path(dirname)
            os.mkdir(full_path)
            log('Created ' + full_path)

        log('INIT: ' + path)
        validateRootDirs(roots)
        traverse(ufspath(self.roots[0]), on_file, on_dir)

    def init_raid4(self, path):
        def on_file(root, filename):
            log('found ' + filename)

            if os.path.isfile(self._full_path(''.join(filename.split('.')[:-2]))):
                log('file ' + str(filename.split('.')[:-2][0]) + ' already constructed. skipping...')
                return

            file_piece = fileToFilePiece(root + '/' + filename)
            if file_piece.typ == 'raw':
                other_file_pieces = { file_piece.numer: file_piece }
            else:
                other_file_pieces = { 'xor': file_piece }

            for other_root in self.roots[0:]:
                if(ufspath(other_root) == root):
                    continue
                temp = filename.split('.')
                for i in range(1, file_piece.denom+1):
                    if i in other_file_pieces:
                        continue

                    temp[-2] = str(i)
                    new_filename = '.'.join(temp)
                    if os.path.isfile(ufspath(other_root, new_filename)):
                        log('found %s in %s' % (new_filename, other_root))
                        new_file_piece = fileToFilePiece(ufspath(other_root, new_filename))
                        other_file_pieces[new_file_piece.numer] = new_file_piece
                        break
                else:
                    for i in range(0,file_piece.denom):
                        temp[-2] = 'xor%d' % i
                        new_filename = '.'.join(temp)
                        if os.path.isfile(ufspath(other_root, new_filename)):
                            log('found %s in %s' % (new_filename, other_root))
                            other_file_pieces['xor'] = fileToFilePiece(ufspath(other_root, new_filename))
                            break
                    #else:
                        #log('no piece found for ' + filename)
                        #return

            if len(other_file_pieces) < file_piece.denom-1:
                log('not enough pieces to recover ' + filename)
                return

            for i in range(1,file_piece.denom+1):
                if i not in other_file_pieces:
                    log("didn't find piece %d of %s: reconstructing it now" % (i, file_piece.basename))

                    extra_bytes = other_file_pieces['xor'].extra_bytes

                    pieces_contents = []
                    for piece in other_file_pieces.values():
                        if piece.typ == 'raw' and piece.numer == file_piece.denom:
                            log('appending %d bytes to piece %d before xor' % (extra_bytes, piece.denom))
                            pieces_contents.append(
                                    open(piece.path(), 'r').read()
                                    + '\0'*extra_bytes)
                        else:
                            pieces_contents.append(open(piece.path(), 'r').read())

                    piece_i_contents = xor_strings(*pieces_contents)
                    if i == file_piece.denom:
                        piece_i_contents = piece_i_contents[:-extra_bytes]

                    log('writing piece %d to /tmp/foo.1.1' % i)
                    with open('/tmp/foo.1.1', 'w') as temp_handle:
                        temp_handle.write(xor_strings(*pieces_contents))

                    other_file_pieces[i] = RawFilePiece('/tmp/foo', 1, 1)

            full_path = self._full_path(''.join(filename.split('.')[:-2]))
            log('reconstructing %s from pieces' % full_path)
            with open(full_path, 'w') as dest:
                for i in range(1, file_piece.denom+1):
                    log('reconstructing using piece %d: %s' % (i, other_file_pieces[i].path()))
                    dest.write(open(other_file_pieces[i].path(), 'r').read())

        def on_dir(dirname):
            full_path = self._full_path(dirname)
            os.mkdir(full_path)
            log('Created ' + full_path)

        log('INIT: ' + path)
        for other_root in self.roots[0:]:
            traverse(ufspath(other_root), on_file, on_dir)

    def link(self, target, name):
        log('LINK ' + path)
        return os.link(self._full_path(target), self._full_path(name))

    def mkdir(self, path, mode):
        log('MKDIR ' + path)
        return os.mkdir(path, mode)

    def mknod(self, path, mode, dev):
        log('MKNOD ' + path)
        return os.mknod(self._full_path(path), mode, dev)

    def open(self, path, flags):
        log('OPEN ' + path)
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def read(self, path, length, offset, fh):
        log('READ ' + path)
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def readdir(self, path, fh):
        log('READDIR ' + path)
        full_path = self._full_path(path)
        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        log('READLINK ' + path)
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def release(self, path, fh):
        log('RELEASE ' + path)
        return os.close(fh)

    def rename(self, old, new):
        log('RENAME ' + path)
        return os.rename(self._full_path(old), self._full_path(new))

    def statfs(self, path):
        log('STATFS ' + path)
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

    def symlink(self, target, name):
        log('SYMLINK ' + path)
        return os.symlink(self._full_path(target), self._full_path(name))

    def truncate(self, path, length, fh=None):
        log('TRUNCATE ' + path)
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def unlink(self, path):
        log('UNLINK ' + path)
        return os.unlink(self._full_path(path))

    def utimens(self, path, times=None):
        log('UTIMENS ' + path)
        return os.utime(self._full_path(path), times)

    def write(self, path, buf, offset, fh):
        log('WRITE ' + path)
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

def error(*args):
    print("ERROR: ", *args, file=sys.stderr)
    exit(1)

def log(*args):
    print(*args, file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 5:
        error('Usage: %s [--raid0|--raid4] <mountpoint> [<sub-filesystems>]' % sys.argv[0])

    FUSE(
        UnifiedCloudStorage(sys.argv[1], sys.argv[3:]),
        sys.argv[2],
        foreground=True)
