import os

# xor_strings("foo", "bar", "baz") = "foo" xor "bar" xor "baz"
def xor_strings(str1, *strs):
    for s in strs:
        str1 = "".join(chr(ord(x) ^ ord(y)) for x,y in zip(str1,s))
    return str1

def directory_dict(path):
    ret = {}
    for child in os.listdir(path):
        fullpath = path + '/' + child
        if os.path.isfile(fullpath):
            ret[child] = {}
        elif os.path.isdir(fullpath):
            ret[child] = directory_dict(fullpath)
    return ret

# Traverse a directory hierarchy, calling on_file on files
# and on_dir on directories. The path passed to each function
# is the path RELATIVE to the root (first argument).
#
# ex:
#
# root/
#     foo/
#         bar
#     baz
#
# traverse(root, print, print)
#
# prints:
#
# foo
# foo/bar
# baz
#
# traverse :: FilePath -> (FilePath -> IO ()) -> (FilePath -> IO ()) -> IO ()
def traverse(path, on_file, on_dir):
    for child in os.listdir(path):
        fullpath = path + '/' + child
        if os.path.isfile(fullpath):
            on_file(child)
        elif os.path.isdir(fullpath):
            on_dir(child)
            traverse_(path, child, on_file, on_dir)

def traverse_(root, relroot, on_file, on_dir):
    fullroot = root + '/' + relroot
    for child in os.listdir(fullroot):
        fullpath = fullroot + '/' + child
        relpath = relroot + '/' + child
        if os.path.isfile(fullpath):
            on_file(relpath)
        elif os.path.isdir(fullpath):
            on_dir(relpath)
            traverse_(root, relpath, on_file, on_file, on_dir)

# foo.1.4
class RawFilePiece:
    def __init__(self, basename, numer, denom):
        self.typ = 'raw'
        self.basename = basename
        self.numer = numer
        self.denom = denom

    def path(self):
        return '%s.%d.%d' % (self.basename, self.numer, self.denom)

# foo.xor1.4
class XorFilePiece:
    def __init__(self, basename, extra_bytes, denom):
        self.typ = 'xor'
        self.basename = basename
        self.extra_bytes = extra_bytes
        self.denom = denom

    def path(self):
        return '%s.xor%d.%d' % (self.basename, self.extra_bytes, self.denom)

def fileToFilePiece(filename):
    dirname = os.path.dirname(filename)
    basename = os.path.basename(filename)
    split_basename = basename.split('.')

    if len(split_basename) < 3:
        raise Exception('bad filename: ' + filename)

    # foobar/foo.txt.1.4 -> foobar/foo.txt
    orig_filename = os.path.join(dirname, ''.join(split_basename[:-2]))

    if split_basename[-2].startswith('xor'):
        return XorFilePiece(
                orig_filename,
                int(split_basename[-2][-1]),
                int(split_basename[-1]))
    else:
        return RawFilePiece(
                orig_filename,
                int(split_basename[-2]),
                int(split_basename[-1]))
