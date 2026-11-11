"""Run AlignTac student jobs on any machine (Colab / local GPU) with resume and periodic sync of the run folders.
jobs file (tab separated, '#' comments):   <prefix> <run> <eval: testA|loo3|s2half|none> [TRAIN_YAML=...]
   e.g.   rss2_   A_loo3_obsf_seed1   loo3
A job with runs/<prefix><run>/final.pt is skipped (only its evaluation is run if results are missing); one with latest.pt is resumed.
usage (from the AlignTac folder):
  python portable/run_jobs.py --jobs portable/jobs_loo3.tsv --parallel 1 --sync-to /content/drive/MyDrive/aligntac_runs
  python portable/run_jobs.py --bench            # 1 epoch of a K=25 student: steps/s, peak VRAM, time estimates
--parallel: about 5.5 GB VRAM per job at batch 32 (8 GB card: 1; T4 16 GB: 2; L4 24 GB: 3-4; A100 40 GB: 6), limited by CPU cores (8 loader workers per job by default; --workers lowers it).
"""
import argparse, glob, json, os, shutil, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = "ablation/pilot_robosoft"; RESULTS = [f"{P}/rss2_testA_results.json", f"{P}/loo3_results.json", f"{P}/rss2_cross_session_results.json"]


def gpu_mem():
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split()[0])
    except Exception:
        return 0


def sync(dst, names):
    if not dst:
        return
    os.makedirs(dst, exist_ok=True)
    for n in names:
        src = os.path.join("runs", n)
        if os.path.isdir(src):
            os.makedirs(os.path.join(dst, n), exist_ok=True)
            for f in os.listdir(src):
                s, d = os.path.join(src, f), os.path.join(dst, n, f)
                if os.path.isfile(s) and (not os.path.exists(d) or os.path.getmtime(s) > os.path.getmtime(d) + 1) and not f.startswith("latest.pt.tmp"):
                    shutil.copy2(s, d + ".part"); os.replace(d + ".part", d)
    os.makedirs(os.path.join(dst, "_results"), exist_ok=True)
    for f in RESULTS + glob.glob("outputs/rss_logs/*.log"):
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(dst, "_results", os.path.basename(f)))


def restore(dst, names):
    for n in names:
        s = os.path.join(dst or "", n)
        if dst and os.path.isdir(s) and not os.path.exists(os.path.join("runs", n, "latest.pt")):
            os.makedirs(os.path.join("runs", n), exist_ok=True)
            for f in os.listdir(s):
                if os.path.isfile(os.path.join(s, f)):
                    shutil.copy2(os.path.join(s, f), os.path.join("runs", n, f))
            print(f"restored {n} from {dst}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs"); ap.add_argument("--parallel", type=int, default=1); ap.add_argument("--sync-to", default=None); ap.add_argument("--sync-every", type=float, default=20, help="minutes")
    ap.add_argument("--workers", type=int, default=None, help="dataloader workers per job (default: the training yaml's 8)"); ap.add_argument("--bench", action="store_true")
    args = ap.parse_args(); os.chdir(ROOT); os.makedirs("outputs/rss_logs", exist_ok=True); os.makedirs("runs_local", exist_ok=True)
    env = dict(os.environ, PY=os.environ.get("PY", sys.executable + " -u"), RUNS_DIR=os.path.join(ROOT, "runs_local"), CUDA_VISIBLE_DEVICES=os.environ.get("CUDA_VISIBLE_DEVICES", "0"),
               PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD="1")   # torch >= 2.6 defaults to weights_only=True; our checkpoints hold optimizer state
    if args.bench:
        import yaml
        name = "_bench"; shutil.rmtree("runs/" + name, ignore_errors=True); shutil.rmtree("runs_local/" + name, ignore_errors=True); os.makedirs("runs/" + name, exist_ok=True)
        steps = None; t0 = time.time(); peak = 0
        cmd = env["PY"].split() + ["-m", "vistacfusion.engine.train", "--model", "ablation/encoder/tac_sitr_single.yaml", "--train", f"{P}/train_pilot_e150_pm.yaml",
                                   "--data", f"{P}/data_T_k25_rf.yaml", "--output-dir", "runs/" + name, "--epochs", "1"]
        p = subprocess.Popen(cmd, env=dict(env, PYTHONPATH=ROOT), stdout=open("outputs/rss_logs/_bench.log", "w"), stderr=subprocess.STDOUT)
        t_first = None
        while p.poll() is None:
            time.sleep(5); peak = max(peak, gpu_mem())
            log = open("outputs/rss_logs/_bench.log").read()
            if t_first is None and "step 0050/" in log:
                t_first = time.time(); steps = int(log.split("step 0050/")[1][:4])
            if t_first and "step 0200/" in log and steps:
                rate = 150 / (time.time() - t_first); p.terminate()
                print(f"training speed {rate:.2f} steps/s at batch 32, peak GPU memory {peak} MiB (whole card)")
                for nm, st in (("K=25 student (150 epochs x 229 steps)", 150 * 229), ("new-object student (150 x 523)", 150 * 523)):
                    print(f"  {nm}: about {st / rate / 3600 * 1.08:.1f} h incl. validation")
                return
        print("benchmark did not reach step 200; see outputs/rss_logs/_bench.log"); return
    jobs = []
    for line in open(args.jobs):
        f = line.split("#")[0].split()
        if len(f) >= 3:
            jobs.append(dict(prefix=f[0], run=f[1], ev=f[2], extra=dict(x.split("=", 1) for x in f[3:]), name=f[0] + f[1]))
    names = [j["name"] for j in jobs]; restore(args.sync_to, names)
    running, pending, last = {}, list(jobs), time.time()
    while pending or running:
        for n, p in list(running.items()):
            if p.poll() is not None:
                print(time.strftime("%m-%d %H:%M"), "finished" if p.returncode == 0 else "FAILED", n, flush=True); del running[n]; sync(args.sync_to, names)
        while pending and len(running) < args.parallel:
            j = pending.pop(0); n = j["name"]; rd = os.path.join("runs", n)
            cmd = ["bash", f"{P}/rss2_train.sh", j["prefix"], j["run"], j["ev"]]
            if os.path.exists(os.path.join(rd, "latest.pt")) and not os.path.exists(os.path.join(rd, "final.pt")):
                cmd += ["--resume", os.path.join(rd, "latest.pt")]
            e = dict(env, **j["extra"])
            if args.workers is not None:
                import yaml
                ty = j["extra"].get("TRAIN_YAML") or f"{P}/train_pilot_e150_pm" + ("_" + j["run"].rsplit("_", 1)[1] if j["run"].rsplit("_", 1)[-1].startswith("seed") else "") + ".yaml"
                c = yaml.safe_load(open(ty)); c["num_workers"] = args.workers; ty2 = f"outputs/rss_logs/_train_{n}.yaml"; yaml.safe_dump(c, open(ty2, "w"), sort_keys=False); e["TRAIN_YAML"] = ty2
            running[n] = subprocess.Popen(cmd, env=e, stdout=open("outputs/rss_logs/rss2_train.log", "a"), stderr=subprocess.STDOUT)
            print(time.strftime("%m-%d %H:%M"), "start", n, "(resume)" if "--resume" in cmd else "", flush=True); time.sleep(30)
        time.sleep(30)
        if time.time() - last > args.sync_every * 60:
            sync(args.sync_to, names); last = time.time()
    sync(args.sync_to, names); print("all jobs done; results in", RESULTS)


if __name__ == "__main__":
    main()
