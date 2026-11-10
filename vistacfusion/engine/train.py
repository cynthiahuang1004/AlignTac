"""Training loop with modality dropout + multi-GPU DDP support.

Single GPU:
    python -m vistacfusion.engine.train --model configs/model.yaml \
           --train configs/train.yaml --data configs/data.yaml

Multi-GPU (e.g. 2 GPUs):
    torchrun --nproc_per_node=2 -m vistacfusion.engine.train \
           --model configs/model.yaml --train configs/train.yaml --data configs/data.yaml
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import time

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
from torch.utils.tensorboard import SummaryWriter

from ..data.dataset import build_datasets
from ..losses.total import MultiTaskLoss
from ..models.model import build_model
from ..utils.config import merge_configs
from ..utils.misc import param_count_str, set_seed
from .eval import evaluate, precompute_encoder_cache


def is_distributed():
    return dist.is_available() and dist.is_initialized()


def is_main_process():
    return not is_distributed() or dist.get_rank() == 0


def setup_distributed():
    if "RANK" not in os.environ:
        return None, 0, 1
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world_size = dist.get_world_size()
    torch.cuda.set_device(local_rank)
    return torch.device(f"cuda:{local_rank}"), rank, world_size


def sample_config(md_cfg):
    if not md_cfg.get("enabled", True):
        return "both"
    r = random.random()
    p_both = md_cfg.p_both
    p_tac = md_cfg.p_tactile_only
    if r < p_both:
        return "both"
    if r < p_both + p_tac:
        return "tactile"
    return "rgb"


def sync_config(config, device):
    """Broadcast modality config from rank 0 so all GPUs use the same config per step."""
    if not is_distributed():
        return config
    mapping = {"both": 0, "tactile": 1, "rgb": 2}
    reverse = {0: "both", 1: "tactile", 2: "rgb"}
    t = torch.tensor([mapping[config]], device=device)
    dist.broadcast(t, src=0)
    return reverse[t.item()]


def move_batch(batch, device):
    return {k: (v.to(device, non_blocking=True) if torch.is_tensor(v) else v)
            for k, v in batch.items()}


def build_scheduler(optimizer, cfg, steps_per_epoch):
    sched_cfg = cfg.schedule
    warmup_steps = sched_cfg.get("warmup_steps", 0)
    max_epochs = sched_cfg.max_epochs
    total_steps = max_epochs * steps_per_epoch
    min_lr_ratio = sched_cfg.get("min_lr_ratio", 0.01)

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(warmup_steps, 1)
        progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
        return min_lr_ratio + 0.5 * (1.0 - min_lr_ratio) * (1 + math.cos(math.pi * progress))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def sample_dpt_inject(md_cfg):
    """Independently sample whether to inject RGB into DPT taps."""
    p = md_cfg.get("p_dpt_inject", 0.5)
    return random.random() < p


def sync_bool(val, device):
    """Broadcast a boolean from rank 0."""
    if not is_distributed():
        return val
    t = torch.tensor([int(val)], device=device)
    dist.broadcast(t, src=0)
    return bool(t.item())


# ----------------------------------------------------------------------------- mean teacher (RSS round 2 baseline)
# Enabled only by `mean_teacher: {enabled: true, ...}` in the train yaml; default behaviour is unchanged.
#   labeled sample   = batch["pose_valid"] == 1 (true label);   unlabeled = pose_valid == 0 (pseudo-labeled root: its depth /
#   normal / pose targets are loaded by the dataset but NEVER enter a loss here).
#   student: strongly photometrically augmented view; EMA teacher: the clean view.  Supervised loss on the labeled samples,
#   consistency (MSE on depth + normals) between student and teacher on all samples, sigmoid ramp-up of its weight.
def mt_strong_aug(x):
    """Photometric augmentation of a normalized image batch (no geometric change, so targets need no warping)."""
    b, dev = x.shape[0], x.device
    gain = 1 + 0.4 * (torch.rand(b, 1, 1, 1, device=dev) - 0.5)
    cgain = 1 + 0.2 * (torch.rand(b, 3, 1, 1, device=dev) - 0.5)
    bias = 0.6 * (torch.rand(b, 3, 1, 1, device=dev) - 0.5)
    noise = torch.randn_like(x) * (0.15 * torch.rand(b, 1, 1, 1, device=dev))
    return x * gain * cgain + bias + noise


def mt_labeled_flags(train_ds):
    """True for samples with a true label (pose json without the "pseudo" flag), in the index order of train_ds."""
    import os.path as osp
    parts = getattr(train_ds, "datasets", [train_ds])
    flags, cache = [], {}
    for ds in parts:
        if id(ds) not in cache:
            fl = []
            for unit, idx in ds.samples:
                with open(osp.join(unit, "raw_data", f"{idx:04d}_pose.json")) as f:
                    fl.append(not json.load(f).get("pseudo", False))
            cache[id(ds)] = fl
        flags += cache[id(ds)]
    return torch.tensor(flags, dtype=torch.bool)


def mt_weight(mt, step):
    ramp = max(1, int(mt["rampup_steps"]))
    t = min(1.0, step / ramp)
    return mt["weight"] * math.exp(-5.0 * (1.0 - t) ** 2)


@torch.no_grad()
def mt_ema_update(mt, student, step):
    d = min(1.0 - 1.0 / (step + 1), mt["decay"])
    for p_t, p_s in zip(mt["teacher"].parameters(), student.parameters()):
        if p_s.requires_grad:
            p_t.mul_(d).add_(p_s.detach(), alpha=1.0 - d)
    for b_t, b_s in zip(mt["teacher"].buffers(), student.buffers()):
        b_t.copy_(b_s)


def train_one_epoch(model, loader, optimizer, scheduler, scaler, criterion,
                    cfg, device, epoch, writer=None, mt=None):
    model.train()
    md_cfg = cfg.modality_dropout
    _mt = cfg.get("model_type", "visuo_tactile")
    is_single = _mt in ("single_encoder", "mvitac", "vital")
    has_dense = _mt not in ("mvitac",)  # vital has DPT; mvitac does not
    running = {}
    global_step_base = epoch * len(loader)
    for step, batch in enumerate(loader):
        batch = move_batch(batch, device)
        if is_single:
            config = "tactile"
            inject_rgb = False
        else:
            config = sample_config(md_cfg)
            config = sync_config(config, device)
            inject_rgb = sample_dpt_inject(md_cfg)
            inject_rgb = sync_bool(inject_rgb, device)

        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=cfg.amp and device.type == "cuda"):
            obj_ids = batch.get("object")
            domain_ids = batch.get("domain")
            tac_in = mt_strong_aug(batch["tactile"]) if mt is not None else batch["tactile"]
            out = model(batch["rgb"], tac_in, config=config,
                        inject_rgb_to_dpt=inject_rgb, object_ids=obj_ids,
                        domain_ids=domain_ids)
            gt = {"depth": batch["depth"], "normal": batch["normal"],
                  "pose": batch["pose"], "mask": batch.get("mask"), "object": batch.get("object"),
                  "pose_valid": batch.get("pose_valid")}
            if mt is None:
                loss, comps = criterion(out, gt, supervise_dense=has_dense)
            else:
                lab = batch["pose_valid"] > 0.5                       # true-labeled samples only
                nb = lab.shape[0]
                if lab.any():
                    sel = lambda v: v[lab] if (torch.is_tensor(v) and v.dim() > 0 and v.shape[0] == nb) else v  # noqa: E731
                    loss, comps = criterion({k: sel(v) for k, v in out.items()}, {k: sel(v) for k, v in gt.items()},
                                            supervise_dense=has_dense)
                else:
                    loss, comps = out["depth"].sum() * 0.0, {}
                with torch.no_grad():
                    out_t = mt["teacher"](batch["rgb"], batch["tactile"], config=config, inject_rgb_to_dpt=inject_rgb,
                                          object_ids=obj_ids, domain_ids=domain_ids)
                cons = torch.nn.functional.mse_loss(out["depth"].float(), out_t["depth"].float())
                if mt["normal"]:
                    cons = cons + torch.nn.functional.mse_loss(out["normal"].float(), out_t["normal"].float())
                w_cons = mt_weight(mt, global_step_base + step)
                loss = loss + w_cons * cons
                comps["mt_cons"] = cons.detach(); comps["mt_w"] = w_cons; comps["mt_labeled"] = lab.float().mean()

            # L2-SP (Li et al., ICML 2018): pull trainable params toward their values at the
            # start of fine-tuning (set in main() when --finetune and cfg.l2sp_weight > 0).
            raw = model.module if isinstance(model, DDP) else model
            l2sp_ref = getattr(raw, "_l2sp_ref", None)
            if l2sp_ref is not None:
                pen = sum(((p.float() - l2sp_ref[n]) ** 2).sum()
                          for n, p in raw.named_parameters() if n in l2sp_ref)
                loss = loss + cfg.l2sp_weight * pen
                comps["l2sp"] = pen.detach()

            # Sim weight annealing: downweight sim samples' loss
            sim_anneal = cfg.get("sim_weight_annealing", None)
            if sim_anneal and domain_ids is not None:
                max_ep = cfg.schedule.max_epochs
                import math as _math
                w = 0.5 * (1 + _math.cos(_math.pi * epoch / max_ep))
                sim_w = sim_anneal.get("min_weight", 0.0) + w * (1.0 - sim_anneal.get("min_weight", 0.0))
                is_sim = (domain_ids == 0).float()
                sample_weight = torch.where(is_sim.bool(), sim_w, 1.0)
                loss = loss * sample_weight.mean()

        if torch.isnan(loss) or torch.isinf(loss):
            if is_main_process():
                print(f"  [WARN] NaN/Inf loss at epoch {epoch} step {step}, skipping")
            optimizer.zero_grad(set_to_none=True)
            continue

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        if mt is not None:
            mt_ema_update(mt, model.module if isinstance(model, DDP) else model, global_step_base + step)

        for k, v in comps.items():
            running[k] = running.get(k, 0.0) + float(v)

        if is_main_process() and step % cfg.log_every == 0:
            lr_now = optimizer.param_groups[0]["lr"]
            msg = "  ".join(f"{k}={running[k] / (step + 1):.4f}" for k in sorted(running))
            inj = "+rgb" if inject_rgb else ""
            print(f"[epoch {epoch:03d} | step {step:04d}/{len(loader)} | cfg={config:7s}{inj} | "
                  f"lr={lr_now:.2e}] {msg}")

        if is_main_process() and writer is not None and step % cfg.log_every == 0:
            gs = global_step_base + step
            for k, v in comps.items():
                writer.add_scalar(f"train_step/{k}", float(v), gs)
            writer.add_scalar("train_step/lr", optimizer.param_groups[0]["lr"], gs)
    return {k: v / len(loader) for k, v in running.items()}


def save_loss_plots(history, plot_dir):
    """Save loss curve PNGs from accumulated training/val history."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(plot_dir, exist_ok=True)
    epochs = [h["epoch"] for h in history]

    # --- Train losses ---
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Training Loss", fontsize=14)
    for ax, key, label in [
        (axes[0, 0], "total", "Total"),
        (axes[0, 1], "depth", "Depth (MSE)"),
        (axes[0, 2], "normal", "Normal (MSE)"),
        (axes[1, 0], "pose_rot", "Pose Rotation (1-cos)"),
        (axes[1, 1], "pose_trans", "Pose Translation (L1)"),
    ]:
        vals = [h["train"].get(key, float("nan")) for h in history]
        ax.plot(epochs, vals, "b-o", markersize=2)
        ax.set_title(label)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.grid(True, alpha=0.3)
    axes[1, 2].axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(plot_dir, "train_loss.png"), dpi=150)
    plt.close(fig)

    # --- Val metrics per config ---
    for config in ["both", "tactile", "rgb"]:
        if config not in history[0].get("val", {}):
            continue
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle(f"Val Metrics — {config}", fontsize=14)
        for ax, key, label in [
            (axes[0, 0], "depth_mse", "Depth MSE"),
            (axes[0, 1], "normal_mse", "Normal MSE"),
            (axes[0, 2], "pose_rot", "Pose Rot (1-cos)"),
            (axes[1, 0], "pose_trans", "Pose Trans (L1)"),
            (axes[1, 1], "pose_rot_deg", "Pose Rot (°)"),
        ]:
            vals = [h["val"].get(config, {}).get(key, float("nan")) for h in history]
            ax.plot(epochs, vals, "r-o", markersize=2)
            ax.set_title(label)
            ax.set_xlabel("Epoch")
            ax.grid(True, alpha=0.3)
        axes[1, 2].axis("off")
        fig.tight_layout()
        fig.savefig(os.path.join(plot_dir, f"val_{config}.png"), dpi=150)
        plt.close(fig)


def build_optimizer(model, optim_cfg, criterion=None):
    params = list(p for p in model.parameters() if p.requires_grad)
    if criterion is not None:
        params += list(p for p in criterion.parameters() if p.requires_grad)
    return torch.optim.AdamW(
        params, lr=optim_cfg.lr, weight_decay=optim_cfg.weight_decay,
        betas=tuple(optim_cfg.betas),
    )


def save_checkpoint(path, model, optimizer, scheduler, scaler, epoch, best_metric,
                    criterion=None):
    raw_model = model.module if isinstance(model, DDP) else model
    data = {
        "epoch": epoch,
        "model": raw_model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(),
        "scaler": scaler.state_dict(),
        "best_metric": best_metric,
    }
    if criterion is not None:
        data["criterion"] = criterion.state_dict()
    torch.save(data, path)
    print(f"  -> checkpoint saved: {path}")


def load_checkpoint(path, model, optimizer=None, scheduler=None, scaler=None,
                    criterion=None, device="cpu"):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    raw_model = model.module if isinstance(model, DDP) else model
    raw_model.load_state_dict(ckpt["model"])
    if optimizer is not None and "optimizer" in ckpt:
        optimizer.load_state_dict(ckpt["optimizer"])
    if scheduler is not None and "scheduler" in ckpt:
        scheduler.load_state_dict(ckpt["scheduler"])
    if scaler is not None and "scaler" in ckpt:
        scaler.load_state_dict(ckpt["scaler"])
    if criterion is not None and "criterion" in ckpt:
        criterion.load_state_dict(ckpt["criterion"])
    return ckpt.get("epoch", 0), ckpt.get("best_metric", float("inf"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="configs/model.yaml")
    ap.add_argument("--train", default="configs/train.yaml")
    ap.add_argument("--data", default="configs/data.yaml")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--resume", type=str, default=None,
                    help="Path to checkpoint to resume from")
    ap.add_argument("--finetune", action="store_true",
                    help="Load only model weights from --resume, reset optimizer/scheduler")
    ap.add_argument("--output-dir", type=str, default="outputs",
                    help="Directory for checkpoints and logs")
    args = ap.parse_args()

    # Distributed setup (no-op when launched without torchrun)
    ddp_device, rank, world_size = setup_distributed()

    cfg = merge_configs(args.model, args.train, args.data)
    set_seed(cfg.seed + rank)

    if ddp_device is not None:
        device = ddp_device
    else:
        device = torch.device(cfg.device if torch.cuda.is_available() else "cpu")

    if is_main_process():
        print(f"Device: {device} | World size: {world_size}")
        os.makedirs(args.output_dir, exist_ok=True)

    train_ds, val_ds = build_datasets(cfg)
    if is_main_process():
        print(f"Train: {len(train_ds)} samples | Val: {len(val_ds)} samples")

    lc = cfg.loader
    bal_frac = cfg.get("balanced_real_fraction", None)
    if bal_frac is not None and getattr(train_ds, "n_sim", 0) > 0:
        if is_distributed():
            raise NotImplementedError(
                "balanced_real_fraction is single-GPU only; launch without torchrun.")
        from ..data.dataset import BalancedDomainBatchSampler
        batch_sampler = BalancedDomainBatchSampler(
            train_ds.n_sim, train_ds.n_real, cfg.batch_size,
            real_fraction=float(bal_frac), seed=cfg.get("seed", 0))
        if is_main_process():
            print(f"  balanced sampling: {batch_sampler.real_per_batch} real + "
                  f"{batch_sampler.sim_per_batch} sim per batch, "
                  f"{batch_sampler.steps} steps/epoch (1 epoch = 1 real pass)")
        train_sampler = None
        train_loader = DataLoader(
            train_ds, batch_sampler=batch_sampler,
            num_workers=lc.num_workers, pin_memory=lc.pin_memory,
            persistent_workers=lc.persistent_workers and lc.num_workers > 0,
        )
    else:
        sample_weights = getattr(train_ds, "sample_weights", None)
        _mtc = cfg.get("mean_teacher", None)
        if _mtc and _mtc.get("enabled", False) and _mtc.get("labeled_fraction", None) and not is_distributed():
            lab_flags = mt_labeled_flags(train_ds)
            n_l, n_u = int(lab_flags.sum()), int((~lab_flags).sum())
            lf = float(_mtc.labeled_fraction)
            sample_weights = torch.where(lab_flags, lf / max(n_l, 1), (1.0 - lf) / max(n_u, 1)).double()
            train_ds.num_samples = len(train_ds)
            if is_main_process():
                print(f"  mean teacher: {n_l} labeled / {n_u} unlabeled train samples, labeled fraction per batch {lf}")
        if is_distributed():
            if sample_weights is not None:
                raise NotImplementedError(
                    "Weighted sampling (real.sample_ratio) is single-GPU only; "
                    "launch without torchrun.")
            train_sampler = DistributedSampler(train_ds, shuffle=True)
        elif sample_weights is not None:
            from torch.utils.data import WeightedRandomSampler
            train_sampler = WeightedRandomSampler(
                sample_weights,
                num_samples=getattr(train_ds, "num_samples", len(train_ds)),
                replacement=True)
        else:
            train_sampler = None
        train_loader = DataLoader(
            train_ds, batch_size=cfg.batch_size,
            shuffle=(train_sampler is None), sampler=train_sampler,
            num_workers=lc.num_workers, pin_memory=lc.pin_memory,
            drop_last=True,
            persistent_workers=lc.persistent_workers and lc.num_workers > 0,
        )
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False,
                            num_workers=lc.num_workers, pin_memory=lc.pin_memory)

    model = build_model(cfg).to(device)
    if is_main_process():
        print(f"Model: {param_count_str(model)}")

    if is_distributed():
        model = DDP(model, device_ids=[device.index], find_unused_parameters=True)

    criterion = MultiTaskLoss(
        cfg.loss, pose_mode=cfg.heads.pose.pose_mode,
        rot_num_bins=cfg.heads.pose.get("rot_num_bins", 72),
    ).to(device)
    optimizer = build_optimizer(model, cfg.optim, criterion)
    scheduler = build_scheduler(optimizer, cfg, len(train_loader))
    scaler = torch.amp.GradScaler("cuda", enabled=cfg.amp and device.type == "cuda")

    mt = None
    _mtc = cfg.get("mean_teacher", None)
    if _mtc and _mtc.get("enabled", False):
        if is_distributed():
            raise NotImplementedError("mean_teacher is single-GPU only")
        teacher = copy.deepcopy(model).to(device).eval()
        for p_ in teacher.parameters():
            p_.requires_grad_(False)
        mt = {"teacher": teacher, "decay": float(_mtc.get("ema_decay", 0.999)), "weight": float(_mtc.get("weight", 10.0)),
              "rampup_steps": float(_mtc.get("rampup_epochs", 30)) * len(train_loader), "normal": bool(_mtc.get("normal", True)),
              "eval": str(_mtc.get("eval", "ema"))}
        print(f"Mean teacher: decay={mt['decay']} weight={mt['weight']} rampup_steps={mt['rampup_steps']:.0f} eval={mt['eval']}")

    start_epoch = 0
    best_metric = float("inf")
    best_pose_metric = float("inf")
    if args.resume:
        if is_main_process():
            print(f"Resuming from {args.resume}"
                  f"{' (finetune: fresh optimizer/scheduler)' if args.finetune else ''}")
        if args.finetune:
            load_checkpoint(args.resume, model, device=device)
            if cfg.get("l2sp_weight", 0.0) > 0:
                raw = model.module if isinstance(model, DDP) else model
                raw._l2sp_ref = {n: p.detach().float().clone()
                                 for n, p in raw.named_parameters() if p.requires_grad}
                if is_main_process():
                    print(f"  L2-SP: weight={cfg.l2sp_weight}, {len(raw._l2sp_ref)} tensors anchored")
        else:
            start_epoch, best_metric = load_checkpoint(
                args.resume, model, optimizer, scheduler, scaler,
                criterion=criterion, device=device)
            start_epoch += 1
        if is_main_process():
            print(f"  resumed at epoch {start_epoch}, best_metric={best_metric:.4f}")

    # Held-out real objects (real.test_objects): evaluated every epoch, never used
    # for checkpoint selection.
    real_test = getattr(train_ds, "real_test", None)
    test_loader = None
    if real_test is not None and is_main_process():
        test_loader = DataLoader(real_test, batch_size=cfg.batch_size, shuffle=False,
                                 num_workers=lc.num_workers, pin_memory=lc.pin_memory)
    test_enc_cache = None
    val_enc_cache = None
    writer = None
    history = []
    plot_dir = None
    history_path = None
    if is_main_process():
        raw_model = model.module if isinstance(model, DDP) else model
        if hasattr(raw_model, 'tactile_encoder'):
            print("Pre-computing val encoder cache...")
            val_enc_cache = precompute_encoder_cache(raw_model, val_loader, device)
            if test_loader is not None:
                test_enc_cache = precompute_encoder_cache(raw_model, test_loader, device)
        writer = SummaryWriter(log_dir=os.path.join(args.output_dir, "tb"))
        plot_dir = os.path.join(args.output_dir, "plots")
        history_path = os.path.join(args.output_dir, "history.json")
        if os.path.exists(history_path):
            with open(history_path) as f:
                history = json.load(f)

    max_epochs = args.epochs if args.epochs is not None else cfg.schedule.max_epochs
    for epoch in range(start_epoch, max_epochs):
        if train_sampler is not None and hasattr(train_sampler, "set_epoch"):
            train_sampler.set_epoch(epoch)

        t0 = time.time()
        train_metrics = train_one_epoch(
            model, train_loader, optimizer, scheduler, scaler, criterion,
            cfg, device, epoch, writer=writer, mt=mt)
        elapsed = time.time() - t0

        if is_main_process():
            print(f"[epoch {epoch:03d}] train done in {elapsed:.0f}s  "
                  f"avg_total={train_metrics.get('total', 0):.4f}")

            for k, v in train_metrics.items():
                writer.add_scalar(f"train_epoch/{k}", v, epoch)

            raw_model = model.module if isinstance(model, DDP) else model
            if mt is not None and mt["eval"] == "ema":
                raw_model = mt["teacher"]            # evaluate and checkpoint the EMA teacher
            val_metrics = evaluate(raw_model, val_loader, cfg, device,
                                   encoder_cache=val_enc_cache)
            print(f"[epoch {epoch:03d}] val metrics: {val_metrics}")

            for config_name, metrics in val_metrics.items():
                for mk, mv in metrics.items():
                    writer.add_scalar(f"val_{config_name}/{mk}", mv, epoch)

            entry = {"epoch": epoch, "train": train_metrics, "val": val_metrics}
            if test_loader is not None:
                test_metrics = evaluate(raw_model, test_loader, cfg, device,
                                        encoder_cache=test_enc_cache)
                print(f"[epoch {epoch:03d}] held-out test metrics: {test_metrics}")
                for config_name, metrics in test_metrics.items():
                    for mk, mv in metrics.items():
                        writer.add_scalar(f"test_{config_name}/{mk}", mv, epoch)
                entry["test"] = test_metrics
            history.append(entry)
            with open(history_path, "w") as f:
                json.dump(history, f, indent=2)
            save_loss_plots(history, plot_dir)

            # single-config models (single_encoder / mvitac / vital) have no "both" key:
            # fall back to the only config they report so best ckpts are still tracked
            both_metrics = val_metrics.get("both") or (
                next(iter(val_metrics.values())) if val_metrics else {})
            depth_score = both_metrics.get("depth_mse", float("inf"))
            # Select by mean angular error (deg) — the metric the tables report. The
            # 1-cos loss is outlier-dominated and used to pick early epochs whose
            # rot/trans are 1.5-2x worse than the best-rot_deg epoch.
            pose_score = both_metrics.get("pose_rot_deg",
                                          both_metrics.get("pose_rot", float("inf")))

            if depth_score < best_metric:
                best_metric = depth_score
                save_checkpoint(
                    os.path.join(args.output_dir, "best_depth.pt"),
                    raw_model if mt is not None else model, optimizer, scheduler, scaler, epoch, best_metric,
                    criterion=criterion)
                print(f"  ** new best depth: mse={best_metric:.6f}")

            if pose_score < best_pose_metric:
                best_pose_metric = pose_score
                save_checkpoint(
                    os.path.join(args.output_dir, "best_pose.pt"),
                    raw_model if mt is not None else model, optimizer, scheduler, scaler, epoch, best_pose_metric,
                    criterion=criterion)
                print(f"  ** new best pose: rot_deg={best_pose_metric:.4f}")

            save_checkpoint(
                os.path.join(args.output_dir, "latest.pt"),
                model, optimizer, scheduler, scaler, epoch, best_metric,
                criterion=criterion)
            writer.flush()

        if is_distributed():
            dist.barrier()

    if is_main_process():
        # keep the final-epoch weights (latest.pt is overwritten every epoch and may be cleaned up afterwards)
        save_checkpoint(os.path.join(args.output_dir, "final.pt"),
                        model, optimizer, scheduler, scaler, epoch, best_metric, criterion=criterion)
        print("Training complete.")
        if writer is not None:
            writer.close()
    if is_distributed():
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
