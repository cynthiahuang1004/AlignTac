"""Mirror a derived link-root (test split, label subsets ...) of real_filtered onto the corrected labels (real_filtered_kin).

usage: python rss2_recapture/rss2_mirror_kin.py <src root> <dst root>      (refuses to overwrite)
Every symlink whose target lies in gs_blender/real_filtered/ is re-pointed to the same path in gs_blender/real_filtered_kin/; real files and
other links are linked as they are.  Frames, indices and splits stay identical: only the labels (_gt.npy, _pose.json) change.
"""
import os, os.path as osp, sys
A, Bk = "/media/hdd/ihsuan/gs_blender/real_filtered/", "/media/hdd/ihsuan/gs_blender/real_filtered_kin/"
src, dst = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
assert osp.isdir(src) and not osp.exists(dst), "source missing or destination exists"
n = k = 0
for root, dirs, files in os.walk(src):
    out = dst + root[len(src):]; os.makedirs(out, exist_ok=True)
    for name in list(dirs) + files:
        p = osp.join(root, name)
        if osp.islink(p):
            t = os.readlink(p)
            if t.startswith(A):
                t = Bk + t[len(A):]; k += 1
                assert osp.exists(t), t
            os.symlink(t, osp.join(out, name)); n += 1
            if name in dirs:
                dirs.remove(name)
        elif osp.isfile(p):
            os.symlink(p, osp.join(out, name)); n += 1
print(f"{dst}: {n} links, {k} re-pointed to the corrected labels")
