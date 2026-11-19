# -*- coding: utf-8 -*-
import os, glob
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")


def size(pats):
    n = b = 0
    for p in pats:
        for f in glob.glob(p, recursive=True):
            if os.path.isfile(f):
                n += 1
                b += os.path.getsize(f)
    return n, b


groups = {
    "configs": ["configs/*"],
    "configs/rXX.yaml": ["configs/r*.yaml"],
    "datasets": ["datasets/**/*"],
    "knowledge(全部)": ["knowledge/**/*"],
    "knowledge/benchmarks+frameworks+playbooks": ["knowledge/benchmarks.json", "knowledge/frameworks/*", "knowledge/playbooks/*"],
    "knowledge/moves": ["knowledge/moves/*"],
    "knowledge/roles": ["knowledge/roles/*"],
    "pipelines": ["pipelines/*"],
    "pipelines/out": ["pipelines/out/*"],
    "projects": ["projects/**/*"],
    "evals": ["evals/**/*"],
    "evals/analysis": ["evals/analysis/**/*"],
    "evals/consulting": ["evals/consulting/*"],
    "evals/answers": ["evals/answers/*"],
    "fixtures": ["fixtures/**/*"],
    "examples": ["examples/*"],
}
for k, v in groups.items():
    n, b = size(v)
    print(f"{k:<42} files={n:<4} bytes={b:<9} KB={b/1024:.1f}")
