"""Minimal GPU job queue for the RSS round-2 runs.

Jobs file: one job per line, `name<TAB>shell command` (lines starting with # are ignored; lines may be appended while the
queue runs).  Each job gets CUDA_VISIBLE_DEVICES=<gpu>; at most --per-gpu jobs of ours per GPU, and a job only starts on a GPU
with at least --min-free MiB free (teammates' jobs are respected).  State: <jobs>.state.json (name -> queued/running/done/failed).
A job whose name is already done/running is never started again; a failed job is retried once (ground rule: stop after two
failures).  Stop the queue by creating <jobs>.stop (running jobs are left to finish).
usage: nohup python ablation/pilot_robosoft/rss2_queue.py --jobs outputs/rss_logs/rss2_jobs.tsv --gpus 0,1,2,3 --per-gpu 3 &
"""
import argparse, json, os, subprocess, time

ap = argparse.ArgumentParser()
ap.add_argument("--jobs", required=True); ap.add_argument("--gpus", default="0,1,2,3")
ap.add_argument("--per-gpu", type=int, default=3); ap.add_argument("--min-free", type=int, default=9000)
args = ap.parse_args()
state_f = args.jobs + ".state.json"
state = json.load(open(state_f)) if os.path.exists(state_f) else {}
for k, v in state.items():                      # a previous queue died: its running jobs are unknown -> mark for retry
    if v["status"] == "running":
        v["status"] = "queued"
running = {}                                    # name -> (Popen, gpu)
gpus = [int(g) for g in args.gpus.split(",")]
log = lambda m: print(time.strftime("%m-%d %H:%M"), m, flush=True)  # noqa: E731


def free_mib(g):
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits", "-i", str(g)],
                                  capture_output=True, text=True).stdout.strip())
    except Exception:
        return 0


while True:
    for name, (p, g) in list(running.items()):
        rc = p.poll()
        if rc is not None:
            del running[name]
            st = state[name]; st["status"] = "done" if rc == 0 else "failed"; st["fails"] = st.get("fails", 0) + (rc != 0)
            st["end"] = time.strftime("%m-%d %H:%M"); log(f"{'done' if rc == 0 else 'FAILED'} {name} (gpu {g}, rc {rc})")
    jobs = []
    if os.path.exists(args.jobs):
        for line in open(args.jobs).read().splitlines():
            if line.strip() and not line.startswith("#") and "\t" in line:
                n, c = line.split("\t", 1); jobs.append((n.strip(), c.strip()))
    for name, cmd in jobs:
        st = state.setdefault(name, {"status": "queued", "fails": 0})
        if st["status"] in ("done", "running") or name in running:
            continue
        if st["status"] == "failed" and st.get("fails", 0) >= 2:
            continue
        if os.path.exists(args.jobs + ".stop"):
            break
        load = {g: sum(1 for _, gg in running.values() if gg == g) for g in gpus}
        cand = [g for g in gpus if load[g] < args.per_gpu and free_mib(g) >= args.min_free]
        if not cand:
            break
        g = min(cand, key=lambda x: (load[x], x))
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(g), PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
        p = subprocess.Popen(["bash", "-c", cmd], env=env)
        running[name] = (p, g); st.update(status="running", gpu=g, start=time.strftime("%m-%d %H:%M")); log(f"start {name} on gpu {g}")
        time.sleep(20)                          # let the job allocate before the next placement decision
    json.dump(state, open(state_f, "w"), indent=1)
    if os.path.exists(args.jobs + ".stop") and not running:
        log("stop file found, queue exits"); break
    time.sleep(30)
