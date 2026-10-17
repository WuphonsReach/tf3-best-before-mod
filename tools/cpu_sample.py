#!/usr/bin/env python3
"""Sample the game's CPU use per thread, and report it per game month, to compare the mod's log levels.

Sample (start it before or after the game; it waits for the process and stops when the game exits or on Ctrl-C):
    tools/cpu_sample.py sample local/cpu/<name>.csv [--match transportfever] [--pid N] [--interval 5]

Report (the CPU in a run, per thread group; with the game log it also gives CPU-seconds per game month):
    tools/cpu_sample.py report local/cpu/<name>.csv [--log local/logs/stdout-....txt] [--skip 60] [--game-months N]

The mod runs on the simulation threads (the log names them "Simulation Thread" and "Sim Pool N"), so compare those rows between
runs; the whole process also carries rendering and audio, which would drown the difference. Compare CPU per game month, not
per second: at 4x the simulation may be saturated, so CPU % looks alike at every level while the game just runs slower.
The game clock comes from the BEST_BEFORE lines (t= or now=), so at logLevel "off" there is none; pass --game-months instead
(read the in-game dates at the start and end of the window).
"""
import argparse
import csv
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

CLK_TCK = os.sysconf("SC_CLK_TCK")
MONTH = 1461000 / 12  # game clock units; a calendar year is 1,461,000


def find_pid(pattern):
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        try:
            cmd = open(f"/proc/{entry}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        # match the executable (first word), so a shell or editor that merely mentions the name is not picked
        exe = cmd.split(" ", 1)[0]
        if re.search(pattern, os.path.basename(exe), re.I):
            found.append((int(entry), cmd.strip()))
    return found


def read_threads(pid):
    """{tid: (comm, cpu ticks)} for every thread of the process."""
    result = {}
    for tid in os.listdir(f"/proc/{pid}/task"):
        try:
            text = open(f"/proc/{pid}/task/{tid}/stat").read()
        except OSError:
            continue  # the thread ended between the listing and the read
        # comm is in parentheses and may contain spaces, so split around the last ")"
        comm = text[text.index("(") + 1:text.rindex(")")]
        fields = text[text.rindex(")") + 2:].split()
        result[int(tid)] = (comm, int(fields[11]) + int(fields[12]))  # utime + stime
    return result


def sample(path, pattern, pid, interval):
    if pid is None:
        print(f"waiting for a process named like /{pattern}/ ...", file=sys.stderr)
        while pid is None:
            found = find_pid(pattern)
            if len(found) > 1:
                sys.exit("several matches, pass --pid or a narrower --match:\n" + "\n".join(f"  {p}  {c[:120]}" for p, c in found))
            if found:
                pid = found[0][0]
                print(f"sampling pid {pid}: {found[0][1][:120]}", file=sys.stderr)
            else:
                time.sleep(1)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc", "tid", "comm", "cpuTicks"])
        rows = 0
        try:
            while os.path.exists(f"/proc/{pid}"):
                stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                try:
                    threads = read_threads(pid)
                except OSError:
                    break  # the process ended
                for tid, (comm, ticks) in threads.items():
                    w.writerow([stamp, tid, comm, ticks])
                rows += 1
                f.flush()
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
    print(f"{rows} samples written to {path}", file=sys.stderr)


def group_name(comm):
    return re.sub(r"[\s_-]*\d+$", "", comm)  # "Sim Pool 2" and "Sim Pool 3" are one group


def parse_utc(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()


def log_clock(path):
    """[(utc seconds, game clock)] from the BEST_BEFORE lines that carry the game clock."""
    points = []
    for ln in open(path, errors="replace"):
        if "BEST_BEFORE" not in ln:
            continue
        stamp = re.match(r"\[(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)Z", ln)
        clock = re.search(r"\b(?:t|now)=(\d+)", ln)
        if stamp and clock:
            when = datetime.strptime(f"{stamp.group(1)} {stamp.group(2)}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            points.append((when.timestamp(), int(clock.group(1))))
    return points


def report(path, log, skip, game_months):
    series = defaultdict(list)  # tid -> [(utc, ticks)]
    comms = {}
    for row in csv.DictReader(open(path, newline="")):
        series[int(row["tid"])].append((parse_utc(row["utc"]), int(row["cpuTicks"])))
        comms[int(row["tid"])] = row["comm"]
    if not series:
        sys.exit(f"{path}: no samples")
    start = min(s[0][0] for s in series.values()) + skip
    end = max(s[-1][0] for s in series.values())
    if end <= start:
        sys.exit(f"{path}: the run is shorter than --skip {skip}s")

    def ticks_at(samples, when):
        """CPU ticks of one thread at `when`, linear between samples; 0 before the thread existed."""
        if when <= samples[0][0]:
            return samples[0][1]
        if when >= samples[-1][0]:
            return samples[-1][1]
        for (t0, c0), (t1, c1) in zip(samples, samples[1:]):
            if t0 <= when <= t1:
                return c0 + (c1 - c0) * (when - t0) / (t1 - t0) if t1 > t0 else c1
        return samples[-1][1]

    window = end - start
    groups = defaultdict(float)
    for tid, samples in series.items():
        first = samples[0][0]
        # a thread that started inside the window counts from its first sample, at 0 before it
        base = ticks_at(samples, start) if first <= start else 0
        groups[group_name(comms[tid])] += (ticks_at(samples, end) - base) / CLK_TCK

    months = game_months
    clock_note = "from --game-months"
    if months is None and log:
        points = [p for p in log_clock(log) if start <= p[0] <= end]
        if len(points) >= 2 and points[-1][1] > points[0][1]:
            months = (points[-1][1] - points[0][1]) / MONTH
            clock_note = f"from {len(points)} log lines, {points[-1][1] - points[0][1]:,} clock units"
    print(f"{path}: window {window:.0f}s after skipping {skip}s" + (f", {months:.2f} game months ({clock_note})" if months else ""))
    print(f"{'thread group':<22}{'cpu seconds':>13}{'% of one core':>15}" + (f"{'cpu s / game month':>20}" if months else ""))
    total = 0.0
    for name, seconds in sorted(groups.items(), key=lambda kv: -kv[1]):
        total += seconds
        line = f"{name:<22}{seconds:>13.1f}{100 * seconds / window:>15.1f}"
        if months:
            line += f"{seconds / months:>20.2f}"
        print(line)
    line = f"{'all threads':<22}{total:>13.1f}{100 * total / window:>15.1f}"
    if months:
        line += f"{total / months:>20.2f}"
    print(line)
    if not months:
        print("no game clock: pass --log with a log that has t=/now= lines (logLevel summary or higher) or --game-months")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("sample", help="write per-thread CPU samples of the game to a CSV")
    s.add_argument("csv")
    s.add_argument("--match", default="transportfever", help="regex for the executable's name (default transportfever)")
    s.add_argument("--pid", type=int)
    s.add_argument("--interval", type=float, default=5.0)
    r = sub.add_parser("report", help="CPU per thread group from a sample CSV")
    r.add_argument("csv")
    r.add_argument("--log", help="the run's game log, for the game clock")
    r.add_argument("--skip", type=float, default=60.0, help="seconds to ignore at the start (loading) (default 60)")
    r.add_argument("--game-months", type=float, help="game months in the window, when the log has no clock (logLevel off)")
    a = p.parse_args()
    if a.mode == "sample":
        try:
            sample(a.csv, a.match, a.pid, a.interval)
        except KeyboardInterrupt:
            sys.exit("stopped before the game was found")
    else:
        report(a.csv, a.log, a.skip, a.game_months)


if __name__ == "__main__":
    main()
