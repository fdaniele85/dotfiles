#! /home/daniele/.venvs/scripts_1553aca88f67/bin/python3

import os
import re
import argparse
import subprocess
import random
import datetime
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import signal
import sys

running_procs = []
stopping = threading.Event()
completed = 0

# --- Signal handler ---
def handle_sigint(signum, frame):
    if not stopping.is_set():
        print("\nInterruzione ricevuta. Terminazione dei processi in corso...", flush=True)
        stopping.set()
        for p in running_procs:
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(1)
signal.signal(signal.SIGINT, handle_sigint)


def get_input_files(ins_dir, ext):
    files = []
    if os.path.isdir(ins_dir):
        for root, _, i_files in os.walk(ins_dir):
            for f in i_files:
                if f.endswith(ext):
                    files.append(os.path.join(root, f))
    else:
        with open(ins_dir, 'r') as file1:
            for line in file1:
                if not line.startswith('#'):
                    files.append(line.strip())
    return sorted(files)

def get_algs(alg_dir):
    if os.path.isdir(alg_dir):
        return [
            os.path.join(alg_dir, file)
            for file in os.listdir(alg_dir)
            if not file.endswith('.no') and os.access(os.path.join(alg_dir, file), os.X_OK)
        ]
    return [alg_dir]

# --- Parsing argomenti ---
parser = argparse.ArgumentParser(description='Parallel runner')
required = parser.add_argument_group('required named arguments')
required.add_argument("--alg", required=True)
required.add_argument("--res", required=True)
required.add_argument("--ins", required=True)

parser.add_argument("--thread", type=int, default=1)
parser.add_argument("--seeds", type=int, nargs='+')
parser.add_argument("--ext")
parser.add_argument("--noseed", action='store_true')
parser.add_argument("--time", type=int)
parser.add_argument("--log", default="log")

args = parser.parse_args()

# --- Impostazioni iniziali ---
alg_dir = args.alg
res_dir = os.path.abspath(args.res)
ins_dir = args.ins
ext = ".%s" % args.ext if args.ext else ".txt"
threads = args.thread
seeds = args.seeds
max_time = args.time
log_prefix = args.log

hostname = socket.gethostname()

if args.noseed:
    seeds = [1]

os.makedirs(res_dir, exist_ok=True)

# --- Preparazione dei task ---
istanze = {}
mancanti = []

input_files = get_input_files(ins_dir, ext)
for s in seeds:
    for input_file in input_files:
        for alg in get_algs(alg_dir):
            basename = os.path.basename(input_file)
            suffix = ".ris" if args.noseed else "_%s.ris" % s
            ris_file = os.path.join(res_dir, hostname, os.path.basename(alg), re.sub(ext + "$", suffix, basename))
            os.makedirs(os.path.dirname(ris_file), exist_ok=True)
            if not os.path.exists(ris_file):
                mancanti.append((os.path.abspath(alg), os.path.abspath(input_file), ris_file, str(s)))
                istanze[input_file] = random.random()

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
    return ' '.join(parts)

# --- Funzione di esecuzione ---
def run_task(t):
    if stopping.is_set():
        return None

    if len(t) == 6:
        alg, inp, out_file, seed, remaining, thread_id = t
    elif len(t) == 5:
        alg, inp, out_file, seed, remaining = t
        thread_id = 0
    else:
        alg, inp, out_file, seed = t
        remaining = -1
        thread_id = 0

    match = re.search(r"_(\d+)$", threading.current_thread().name)
    log_index = int(match.group(1)) + 1 if match else 0
    log_file = f"/tmp/{log_prefix}{log_index}"

    cmd = [alg, "--log-file", log_file, inp] if args.noseed else [alg, "--seed", seed, "--log-file", log_file, inp]
    print(f"\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} running: {' '.join(cmd)} ({remaining} rimanenti)", flush=True)

    try:
        start = time.time()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        running_procs.append(p)
        out, err = p.communicate()
        duration = time.time() - start
    except Exception as e:
        return f"Errore durante l'esecuzione di {' '.join(cmd)}: {e}", -1

    if stopping.is_set():
        return None

    if p.returncode == 0:
        with open(out_file, "w") as f:
            f.write(out)
        return f"\n{' '.join(cmd)} completato con codice {p.returncode} in {format_time(duration)}\n{out}", p.returncode
    else:
        with open(out_file, "w") as f:
            f.write('')
        return f"\n{' '.join(cmd)} completato con codice {p.returncode} in {format_time(duration)}. STDERR: {err}", p.returncode

# --- Esecuzione parallela ---
start_time = time.time()

with ThreadPoolExecutor(max_workers=threads) as executor:
    pending_counter = len(mancanti)
    future_to_task = {}
    for i, t in enumerate(mancanti, start=1):
        if stopping.is_set():
            break
        t_with_count = t + (pending_counter, i)
        future = executor.submit(run_task, t_with_count)
        future_to_task[future] = t
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
        handle_sigint(None, None)
