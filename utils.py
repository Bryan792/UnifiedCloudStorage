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
def traverse(path, on_file, on_dir):
    print('traverse %s' % path)
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
