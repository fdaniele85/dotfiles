#! /home/daniele/.venvs/scripts_1553aca88f67/bin/python3

import argparse
import datetime
import os
import random
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

running_procs = []
stopping = threading.Event()
completed = 0
termination_signal = None


def handle_stop(signum, frame):
    global termination_signal
    if stopping.is_set():
        return
    termination_signal = signum
    print("\nInterruzione ricevuta. Terminazione dei processi in corso...", flush=True)
    stopping.set()
    for proc in list(running_procs):
        try:
            proc.terminate()
        except Exception:
            pass


signal.signal(signal.SIGINT, handle_stop)
signal.signal(signal.SIGTERM, handle_stop)


def get_input_files(ins_dir, ext):
    files = []
    if os.path.isdir(ins_dir):
        for root, _, i_files in os.walk(ins_dir):
            for file_name in i_files:
                if file_name.endswith(ext):
                    files.append(os.path.join(root, file_name))
    else:
        with open(ins_dir, "r") as file1:
            for line in file1:
                if not line.startswith("#"):
                    files.append(line.strip())
    return sorted(files)


def get_algs(alg_dir):
    if os.path.isdir(alg_dir):
        return [
            os.path.join(alg_dir, file_name)
            for file_name in os.listdir(alg_dir)
            if not file_name.endswith(".no") and os.access(os.path.join(alg_dir, file_name), os.X_OK)
        ]
    return [alg_dir]


def send_ntfy(message, topic, title=None, priority=None, tags=None):
    url = f"https://ntfy.sh/{topic}"
    data = message.encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")

    if title:
        req.add_header("Title", title)
    if priority:
        req.add_header("Priority", str(priority))
    if tags:
        req.add_header("Tags", ",".join(tags))

    try:
        with urllib.request.urlopen(req) as response:
            if 200 <= response.status < 300:
                print(f"Notifica inviata con successo ({response.status})", flush=True)
            else:
                print(f"Warning: invio notifica fallito ({response.status})", flush=True)
    except Exception as exc:
        print(f"Warning: errore durante l'invio della notifica: {exc}", flush=True)


def get_parser():
    parser = argparse.ArgumentParser(description="Parallel runner")
    required = parser.add_argument_group("required named arguments")
    required.add_argument("--alg", required=True)
    required.add_argument("--res", required=True)
    required.add_argument("--ins", required=True)

    parser.add_argument("--thread", type=int, default=1)
    parser.add_argument("--seeds", type=int, nargs="+")
    parser.add_argument("--ext", default=None)
    parser.add_argument("--noseed", action="store_true")
    parser.add_argument("--time", type=int)
    parser.add_argument("--log", default="log")
    parser.add_argument("--mode", choices=["local", "slurm"], default="slurm")
    parser.add_argument("--ntfy", default="Testing")
    parser.add_argument("--shuffle", action="store_true")
    return parser


def format_time(seconds):
    seconds = int(seconds)
    parts = []
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours > 0:
        parts.append(f"{hours} ore")
    if minutes > 0:
        parts.append(f"{minutes} minuti")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} secondi")
    return " ".join(parts)


def build_result_path(res_dir, mode, hostname, alg, input_file, ext, seed, use_seed):
    basename = os.path.basename(input_file)
    suffix = ".ris" if use_seed else f"_{seed}.ris"
    alg_name = os.path.basename(alg)
    if mode == "local":
        base_dir = os.path.join(res_dir, hostname, alg_name)
    else:
        base_dir = os.path.join(res_dir, alg_name)
    return os.path.join(base_dir, re.sub(ext + "$", suffix, basename))


def build_log_file(log_prefix, mode):
    match = re.search(r"_(\d+)$", threading.current_thread().name)
    log_index = int(match.group(1)) + 1 if match else 0
    if mode == "local":
        return f"/tmp/{log_prefix}{log_index}"
    return f"{log_prefix}{log_index}"


def build_command(args, alg, inp, seed, log_file):
    cmd = [alg, inp]
    if not args.noseed:
        cmd.extend(["--seed", seed])
    cmd.extend(["--log-file", log_file])
    return cmd


def remove_running_proc(proc):
    try:
        running_procs.remove(proc)
    except ValueError:
        pass


def run_task(task, args):
    if stopping.is_set():
        return None

    if len(task) == 6:
        alg, inp, out_file, seed, remaining, thread_id = task
    elif len(task) == 5:
        alg, inp, out_file, seed, remaining = task
        thread_id = 0
    else:
        alg, inp, out_file, seed = task
        remaining = -1
        thread_id = 0

    log_file = build_log_file(args.log, args.mode)
    cmd = build_command(args, alg, inp, seed, log_file)
    print(
        f"\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} running: {' '.join(cmd)} ({remaining} rimanenti)",
        flush=True,
    )

    proc = None
    try:
        start = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        running_procs.append(proc)
        out, err = proc.communicate()
        duration = time.time() - start
    except Exception as exc:
        if proc is not None:
            remove_running_proc(proc)
        return f"Errore durante l'esecuzione di {' '.join(cmd)}: {exc}", -1
    finally:
        if proc is not None:
            remove_running_proc(proc)

    if stopping.is_set():
        return None

    if proc.returncode == 0:
        with open(out_file, "w") as file_out:
            file_out.write(out)
        return f"\n{' '.join(cmd)} completato con codice 0 in {format_time(duration)}\n{out}", 0

    with open(out_file, "w") as file_out:
        file_out.write("")
    return (
        f"\n{' '.join(cmd)} completato con codice {proc.returncode} in {format_time(duration)}. STDERR: {err}",
        proc.returncode,
    )


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    alg_dir = args.alg
    res_dir = os.path.abspath(args.res)
    ins_dir = args.ins
    ext = args.ext if args.ext is not None else ".txt"
    threads = args.thread
    seeds = args.seeds
    max_time = args.time
    hostname = socket.gethostname()

    if args.noseed:
        seeds = [1]
    elif not seeds:
        parser.error("--seeds è obbligatorio se non usi --noseed")

    os.makedirs(res_dir, exist_ok=True)

    istanze = {}
    mancanti = []

    input_files = get_input_files(ins_dir, ext)
    for seed in seeds:
        for input_file in input_files:
            for alg in get_algs(alg_dir):
                ris_file = build_result_path(
                    res_dir=res_dir,
                    mode=args.mode,
                    hostname=hostname,
                    alg=alg,
                    input_file=input_file,
                    ext=ext,
                    seed=seed,
                    use_seed=args.noseed,
                )
                os.makedirs(os.path.dirname(ris_file), exist_ok=True)
                if not os.path.exists(ris_file):
                    mancanti.append((os.path.abspath(alg), os.path.abspath(input_file), ris_file, str(seed)))
                    istanze[input_file] = random.random()

    if args.shuffle:
        random.shuffle(mancanti)

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        pending_counter = len(mancanti)
        future_to_task = {}
        for i, task in enumerate(mancanti, start=1):
            if stopping.is_set():
                break
            task_with_count = task + (pending_counter, i)
            future = executor.submit(run_task, task_with_count, args)
            future_to_task[future] = task
            pending_counter -= 1
        try:
            for future in as_completed(future_to_task):
                if stopping.is_set():
                    break
                result = future.result()
                if result is None:
                    continue
                msg, code = result
                print(msg, flush=True)
                completed += 1
                avg_time = (time.time() - start_time) / (completed / threads)
                remaining = len(future_to_task) - completed
                estimate = format_time(avg_time * remaining / threads)
                print(f"\nStima tempo rimanente: {estimate}, tempo medio: {format_time(avg_time)}", flush=True)
                if max_time and time.time() - start_time > max_time:
                    print("Tempo massimo raggiunto", flush=True)
                    stopping.set()
                    break
        except KeyboardInterrupt:
            handle_stop(signal.SIGINT, None)

    if stopping.is_set():
        sys.exit(1)

    if args.mode == "slurm":
        send_ntfy(f"Testing terminato {args.ntfy}", "testing-9391f8f1-3ee6-4919")
