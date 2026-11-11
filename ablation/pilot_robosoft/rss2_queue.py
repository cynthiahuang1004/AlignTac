"""Minimal GPU job queue for the RSS round-2 runs.

Jobs file: one job per line, `name<TAB>shell command` (lines starting with # are ignored; lines may be appended while the
queue runs).  Each job gets CUDA_VISIBLE_DEVICES=<gpu>; at most --per-gpu jobs of ours per GPU, and a job only starts on a GPU
with at least --min-free MiB free (teammates' jobs are respected).  State: <jobs>.state.json (name -> queued/running/done/failed).
A job whose name is already done/running is never started again; a failed job is retried once (ground rule: stop after two
failures).  Stop the queue by creating <jobs>.stop (running jobs are left to finish).
Placement counts EVERY training process of this user on a GPU (nvidia-smi), not only the queue's own, so several queues /
orphaned jobs share the --per-gpu cap.  On restart, jobs recorded as running are re-attached if their rss2_train.sh process is
still alive (status "external") and marked done/failed from the job log when it ends.
usage: nohup python ablation/pilot_robosoft/rss2_queue.py --jobs outputs/rss_logs/rss2_jobs.tsv --gpus 0,1,2,3 --per-gpu 3 &
"""
import argparse, json, os, re, subprocess, time

ap = argparse.ArgumentParser()
ap.add_argument("--jobs", required=True); ap.add_argument("--gpus", default="0,1,2,3")
ap.add_argument("--per-gpu", type=int, default=3); ap.add_argument("--min-free", type=int, default=9000)
ap.add_argument("--job-mib", type=int, default=6000, help="memory reserved for a job this queue started that has not allocated yet")
args = ap.parse_args()
state_f = args.jobs + ".state.json"
state = json.load(open(state_f)) if os.path.exists(state_f) else {}
def alive(name):
    ps = subprocess.run(["ps", "-u", os.environ.get("USER", "shared"), "-o", "args"], capture_output=True, text=True).stdout
    run = name.split("_", 1)[1] if name.startswith(("rss2_", "pilot150_")) else name
    return re.search(rf"rss2_train.sh \S+ {re.escape(run)} ", ps) is not None


def finished_ok(name):
    try:
        return re.search(rf"\[{re.escape(name)}\] done", open("outputs/rss_logs/rss2_train.log").read()) is not None
    except OSError:
        return False


for k, v in state.items():                      # a previous queue died: re-attach its jobs if they still run, else retry them
    if v["status"] == "running":
        v["status"] = "external" if alive(k) else "queued"


def our_gpu_load():
    """{gpu index: number of this user's training processes} from nvidia-smi."""
    load = {g: 0 for g in gpus}
    try:
        uid = os.getuid()
        apps = subprocess.run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid", "--format=csv,noheader"], capture_output=True, text=True).stdout
        uuids = subprocess.run(["nvidia-smi", "--query-gpu=index,gpu_uuid", "--format=csv,noheader"], capture_output=True, text=True).stdout
        u2i = {u.strip(): int(i) for i, u in (l.split(",") for l in uuids.strip().splitlines())}
        for l in apps.strip().splitlines():
            u, pid = (x.strip() for x in l.split(","))
            try:
                if os.stat(f"/proc/{pid}").st_uid == uid and "engine.train" in open(f"/proc/{pid}/cmdline").read():
                    load[u2i[u]] = load.get(u2i[u], 0) + 1
            except (OSError, KeyError):
                pass
    except Exception:
        pass
    return load
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
    for name, st in state.items():                  # re-attached jobs: finished?
        if st["status"] == "external" and not alive(name):
            st["status"] = "done" if finished_ok(name) else "failed"; st["fails"] = st.get("fails", 0) + (st["status"] == "failed")
            st["end"] = time.strftime("%m-%d %H:%M"); log(f"external job {name} ended: {st['status']}")
    jobs = []
    if os.path.exists(args.jobs):
        for line in open(args.jobs).read().splitlines():
            if line.strip() and not line.startswith("#") and "\t" in line:
                n, c = line.split("\t", 1); jobs.append((n.strip(), c.strip()))
    for name, cmd in jobs:
        st = state.setdefault(name, {"status": "queued", "fails": 0})
        if st["status"] in ("done", "running", "external") or name in running:
            continue
        if st["status"] == "failed" and st.get("fails", 0) >= 2:
            continue
        if os.path.exists(args.jobs + ".stop"):
            break
        load = our_gpu_load()                       # all of this user's training jobs, whichever queue started them
        mine = {g: sum(1 for (_p, gg) in running.values() if gg == g) for g in gpus}   # jobs this queue started (may not have allocated yet)
        pend = {g: max(0, mine[g] - load.get(g, 0)) for g in gpus}                      # started but not yet visible on the GPU
        load = {g: max(load.get(g, 0), mine[g]) for g in gpus}
        cand = [g for g in gpus if load[g] < args.per_gpu and free_mib(g) - args.job_mib * pend[g] >= args.min_free]
        if not cand:
            break
        g = min(cand, key=lambda x: (load[x], x))
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(g), PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
        p = subprocess.Popen(["bash", "-c", cmd], env=env)
        running[name] = (p, g); st.update(status="running", gpu=g, start=time.strftime("%m-%d %H:%M")); log(f"start {name} on gpu {g}")
        time.sleep(20)                          # let the job allocate before the next placement decision
    json.dump(state, open(state_f, "w"), indent=1)
    if os.path.exists(args.jobs + ".stop") and not running and not any(v["status"] == "external" for v in state.values()):
        log("stop file found, queue exits"); break
    time.sleep(30)
