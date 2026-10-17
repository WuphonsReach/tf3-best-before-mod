#!/usr/bin/env python3
"""Sample the game's CPU use, and the machine's, and report it per game month, to compare the mod's log levels.

Sample (start it before or after the game; it waits for the process and stops when the game exits or on Ctrl-C):
    tools/cpu_sample.py sample local/cpu/<name> [--match transportfever] [--pid N] [--interval 5]
        [--threads REGEX] [--also REGEX]
  writes two files, appended to (one header each). Every start of the script picks a random 8-character run id (or pass --run-id)
  and puts it on all its rows, so runs sharing a file can be told apart; the report prints each run on its own.
    <name>.process.csv   utc, runId, pid, tid, comm, cpuTicks: the game's threads whose name matches --threads (default the
                         simulation and main threads), and one whole-process row (tid 0) per other process whose name
                         matches --also (default none; say steam|code to see whether something else was busy)
    <name>.system.csv    utc, runId, cpu jiffies by kind from /proc/stat (all cores), the 1-minute load and free memory

Report (CPU in a run, per thread group, the machine's busy share, and with the game log CPU seconds per game month):
    tools/cpu_sample.py report local/cpu/<name> [--log local/logs/stdout-....txt] [--skip 60 | --from HH:MM:SS --until HH:MM:SS] [--game-months N] [--run ID]

The mod runs on the simulation threads (the log names them "Simulation Thread" and "Sim Pool N"), so compare those rows between
runs. Compare CPU per game month, not per second: at 4x the simulation may be saturated, so CPU % looks alike at every level
while the game just runs slower. The game clock comes from the BEST_BEFORE lines (t= or now=), so at logLevel "off" there is
none; pass --game-months instead: calendar months between the in-game dates on screenshots taken at the window's start and end,
with --from and --until set to the screenshots' times (UTC, which is the screenshot's local time plus 4 hours). Game months from
--log are clock months, about a quarter of a calendar month at the usual calendar speed, so never compare the two. Sample for at
least 5 minutes, and compare runs over the same stretch of game time: the game gets heavier as it goes.
"""
import argparse
import csv
import os
import re
import secrets
import string
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

CLK_TCK = os.sysconf("SC_CLK_TCK")
MONTH = 1461000 / 12  # game clock units; a calendar year is 1,461,000
SYSTEM_COLUMNS = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"]
DEFAULT_THREADS = r"^(Sim|Main)"
MIN_INTERVAL, MAX_INTERVAL = 1.0, 10.0


def processes():
    """[(pid, executable basename, comm)] for every process."""
    result = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        try:
            cmd = open(f"/proc/{entry}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
            text = open(f"/proc/{entry}/stat").read()
        except OSError:
            continue
        result.append((int(entry), os.path.basename(cmd.split(" ", 1)[0]), text[text.index("(") + 1:text.rindex(")")]))
    return result


def find_pid(pattern):
    # match the executable (first word of the command line), so a shell or editor that merely mentions the name is not picked
    return [(pid, exe) for pid, exe, _ in processes() if re.search(pattern, exe, re.I)]


def cpu_ticks(path):
    """(comm, utime + stime) from a /proc stat file; comm is in parentheses and may contain spaces."""
    text = open(path).read()
    fields = text[text.rindex(")") + 2:].split()
    return text[text.index("(") + 1:text.rindex(")")], int(fields[11]) + int(fields[12])


def read_threads(pid, wanted):
    """{tid: (comm, ticks)} for the threads of the process whose name matches `wanted`."""
    result = {}
    for tid in os.listdir(f"/proc/{pid}/task"):
        try:
            comm, ticks = cpu_ticks(f"/proc/{pid}/task/{tid}/stat")
        except OSError:
            continue  # the thread ended between the listing and the read
        if wanted.search(comm):
            result[int(tid)] = (comm, ticks)
    return result


def read_system():
    with open("/proc/stat") as f:
        jiffies = f.readline().split()[1:1 + len(SYSTEM_COLUMNS)]
    load = open("/proc/loadavg").read().split()[0]
    available = next((int(ln.split()[1]) for ln in open("/proc/meminfo") if ln.startswith("MemAvailable:")), 0)
    return jiffies + [load, str(available)]


def new_run_id():
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))


def opened(path, header):
    """The file in append mode, with the header only when it is new."""
    fresh = not os.path.exists(path) or os.path.getsize(path) == 0
    f = open(path, "a", newline="")
    w = csv.writer(f)
    if fresh:
        w.writerow(header)
    return f, w


def sample(base, pattern, pid, interval, threads, also, run_id):
    wanted, others = re.compile(threads, re.I), re.compile(also, re.I) if also else None
    if pid is None:
        print(f"waiting for a process named like /{pattern}/ ...", file=sys.stderr)
        while pid is None:
            found = find_pid(pattern)
            if len(found) > 1:
                sys.exit("several matches, pass --pid or a narrower --match:\n" + "\n".join(f"  {p}  {c}" for p, c in found))
            if found:
                pid = found[0][0]
                print(f"sampling pid {pid} ({found[0][1]}) every {interval:g}s", file=sys.stderr)
            else:
                time.sleep(1)
    os.makedirs(os.path.dirname(os.path.abspath(base)), exist_ok=True)
    pf, pw = opened(base + ".process.csv", ["utc", "runId", "pid", "tid", "comm", "cpuTicks"])
    sf, sw = opened(base + ".system.csv", ["utc", "runId"] + SYSTEM_COLUMNS + ["load1", "memAvailableKb"])
    print(f"run id {run_id}", file=sys.stderr)
    rows = 0
    try:
        while os.path.exists(f"/proc/{pid}"):
            # Each file's rows carry the clock read right before them, so the system row is not labelled with the process
            # scan's time (scanning every process can take tens of milliseconds); the report uses the stamps as they are.
            when = stamp()
            try:
                threads_now = read_threads(pid, wanted)
            except OSError:
                break  # the process ended
            for tid, (comm, ticks) in threads_now.items():
                pw.writerow([when, run_id, pid, tid, comm, ticks])
            if others is not None:
                for other, _, comm in processes():
                    if other != pid and others.search(comm):
                        when_other = stamp()
                        try:
                            pw.writerow([when_other, run_id, other, 0, comm, cpu_ticks(f"/proc/{other}/stat")[1]])
                        except OSError:
                            pass  # the process ended
            when = stamp()
            sw.writerow([when, run_id] + read_system())
            pf.flush()
            sf.flush()
            rows += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    print(f"{rows} samples of run {run_id} appended to {base}.process.csv and {base}.system.csv", file=sys.stderr)


def stamp():
    """The wall clock now, taken from the nanosecond clock and written to the microsecond. The /proc counters only tick every
    10 ms, so this is finer than they resolve; what matters is that it is taken right before the reads it labels."""
    ns = time.time_ns()
    return datetime.fromtimestamp(ns // 1_000_000_000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ns % 1_000_000_000 // 1000:06d}Z"


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


def value_at(samples, when):
    """A cumulative counter at `when`, linear between samples [(utc, value)]."""
    if when <= samples[0][0]:
        return samples[0][1]
    if when >= samples[-1][0]:
        return samples[-1][1]
    for (t0, c0), (t1, c1) in zip(samples, samples[1:]):
        if t0 <= when <= t1:
            return c0 + (c1 - c0) * (when - t0) / (t1 - t0) if t1 > t0 else c1
    return samples[-1][1]


def report(base, log, skip, game_months, only_run, from_at=None, until_at=None):
    process_path = base if base.endswith(".csv") else base + ".process.csv"
    system_path = None if base.endswith(".csv") else base + ".system.csv"
    runs = defaultdict(lambda: defaultdict(list))  # run id -> (pid, tid) -> [(utc, ticks)]
    comms = {}
    for row in csv.DictReader(open(process_path, newline="")):
        key = (int(row["pid"]), int(row["tid"]))
        runs[row["runId"]][key].append((parse_utc(row["utc"]), int(row["cpuTicks"])))
        comms[key] = row["comm"]
    system = defaultdict(list)
    if system_path and os.path.exists(system_path):
        for row in csv.DictReader(open(system_path, newline="")):
            system[row["runId"]].append(row)
    if only_run:
        runs = {r: v for r, v in runs.items() if r == only_run}
    if not runs:
        sys.exit(f"{process_path}: no samples" + (f" for run {only_run}" if only_run else ""))
    for run, series in sorted(runs.items(), key=lambda kv: min(s[0][0] for s in kv[1].values())):
        report_run(run, series, comms, system.get(run, []), process_path, log, skip, game_months, from_at, until_at)


def report_run(run, series, comms, system_rows, process_path, log, skip, game_months, from_at, until_at):
    for samples in series.values():
        samples.sort()
    first = min(s[0][0] for s in series.values())
    last = max(s[-1][0] for s in series.values())
    day = datetime.fromtimestamp(first, timezone.utc).strftime("%Y-%m-%d")
    at = lambda hms: datetime.strptime(f"{day} {hms}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    start = at(from_at) if from_at else first + skip
    end = min(at(until_at), last) if until_at else last
    print(f"\n=== run {run}: started {datetime.fromtimestamp(first, timezone.utc):%Y-%m-%d %H:%M:%SZ} ===")
    if end <= start:
        print(f"the run is shorter than --skip {skip:g}s")
        return
    window = end - start

    game, other = defaultdict(float), defaultdict(float)
    for key, samples in series.items():
        # a thread that started inside the window counts from its first sample, at 0 before it
        base_ticks = value_at(samples, start) if samples[0][0] <= start else 0
        seconds = (value_at(samples, end) - base_ticks) / CLK_TCK
        if key[1] == 0:
            other[comms[key]] += seconds
        else:
            game[group_name(comms[key])] += seconds

    months = game_months
    clock_note = "from --game-months"
    if months is None and log:
        points = [p for p in log_clock(log) if start <= p[0] <= end]
        if len(points) >= 2 and points[-1][1] > points[0][1]:
            months = (points[-1][1] - points[0][1]) / MONTH
            clock_note = f"clock months, from {len(points)} log lines, {points[-1][1] - points[0][1]:,} clock units"
    print(f"{process_path}: window {window:.0f}s after skipping {skip:g}s"
          + (f", {months:.2f} game months ({clock_note})" if months else "")
          + f", from {datetime.fromtimestamp(start, timezone.utc):%H:%M:%S}Z to {datetime.fromtimestamp(end, timezone.utc):%H:%M:%S}Z")
    if window < 300:
        print("WARNING  under 5 minutes: too short to compare log levels")

    def table(title, groups, total_label):
        print(f"\n{title:<22}{'cpu seconds':>13}{'% of one core':>15}" + (f"{'cpu s / game month':>20}" if months else ""))
        total = 0.0
        for name, seconds in sorted(groups.items(), key=lambda kv: -kv[1]):
            total += seconds
            line = f"{name:<22}{seconds:>13.1f}{100 * seconds / window:>15.1f}"
            print(line + (f"{seconds / months:>20.2f}" if months else ""))
        if total_label:
            line = f"{total_label:<22}{total:>13.1f}{100 * total / window:>15.1f}"
            print(line + (f"{total / months:>20.2f}" if months else ""))

    table("game thread group", game, "all sampled threads")
    if other:
        table("other process", other, None)

    if system_rows:
        cols = defaultdict(list)
        for row in system_rows:
            for name in SYSTEM_COLUMNS:
                cols[name].append((parse_utc(row["utc"]), int(row[name])))
        delta = {n: value_at(cols[n], end) - value_at(cols[n], start) for n in SYSTEM_COLUMNS}
        total = sum(delta.values())
        if total > 0:
            idle = delta["idle"] + delta["iowait"]
            inside = [r for r in system_rows if start <= parse_utc(r["utc"]) <= end]
            loads = [float(r["load1"]) for r in inside]
            free = [int(r["memAvailableKb"]) for r in inside]
            print(f"\nwhole machine ({os.cpu_count()} cores): busy {100 * (1 - idle / total):.1f}%"
                  f" (user {100 * (delta['user'] + delta['nice']) / total:.1f}%, system {100 * delta['system'] / total:.1f}%,"
                  f" iowait {100 * delta['iowait'] / total:.1f}%, irq/softirq {100 * (delta['irq'] + delta['softirq']) / total:.1f}%,"
                  f" steal {100 * delta['steal'] / total:.1f}%)"
                  + (f"; load1 {min(loads):.1f} to {max(loads):.1f}; free memory min {min(free) / 1024:,.0f} MB" if loads else ""))
    if not months:
        print("\nno game clock: pass --log with a log that has t=/now= lines (logLevel summary or higher) or --game-months")


def interval_arg(text):
    value = float(text)
    if not MIN_INTERVAL <= value <= MAX_INTERVAL:
        raise argparse.ArgumentTypeError(f"the interval is {MIN_INTERVAL:g} to {MAX_INTERVAL:g} seconds")
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("sample", help="append CPU samples of the game and the machine to <name>.process.csv and <name>.system.csv")
    s.add_argument("name", help="path prefix of the two files")
    s.add_argument("--match", default="transportfever", help="regex for the executable's name (default transportfever)")
    s.add_argument("--pid", type=int)
    s.add_argument("--interval", type=interval_arg, default=5.0, help="seconds between samples, 1 to 10 (default 5)")
    s.add_argument("--threads", default=DEFAULT_THREADS, help=f"regex for the game thread names to record (default {DEFAULT_THREADS})")
    s.add_argument("--also", default="", help="regex for other process names to record as one row each (default none)")
    s.add_argument("--run-id", help="the run id to put on every row (default: 8 random lowercase letters and digits)")
    r = sub.add_parser("report", help="CPU per thread group and the machine's load from the two files")
    r.add_argument("name", help="the sample prefix (or a .process.csv path)")
    r.add_argument("--log", help="the run's game log, for the game clock")
    r.add_argument("--skip", type=float, default=60.0, help="seconds to ignore at the start (loading) (default 60)")
    r.add_argument("--game-months", type=float, help="game months in the window, when the log has no clock (logLevel off)")
    r.add_argument("--from", dest="from_at", help="window start, HH:MM:SS UTC on the run's day (instead of --skip)")
    r.add_argument("--until", dest="until_at", help="window end, HH:MM:SS UTC (default: the last sample)")
    r.add_argument("--run", help="report only this run id (default: every run in the files, one after another)")
    a = p.parse_args()
    if a.mode == "sample":
        try:
            sample(a.name, a.match, a.pid, a.interval, a.threads, a.also, a.run_id or new_run_id())
        except KeyboardInterrupt:
            sys.exit("stopped before the game was found")
    else:
        report(a.name, a.log, a.skip, a.game_months, a.run, a.from_at, a.until_at)


if __name__ == "__main__":
    main()
