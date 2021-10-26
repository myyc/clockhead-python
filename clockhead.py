#!/usr/bin/env python3

import time
import os.path

import psutil


ROOT = "/sys/devices/system/cpu"
CPU0 = "/sys/devices/system/cpu/cpu0/cpufreq"


def set_value(fn, v):
    with open(fn, "w") as f:
        f.write(str(v))


def get_value(fn):
    with open(fn, "r") as f:
        return f.read()


def get_frequencies():
    with open(CPU0 + "/scaling_available_frequencies") as f:
        return sorted([int(freq) for freq in f.read().strip().split(" ")])


def get_governors():
    with open(CPU0 + "/scaling_available_governors") as f:
        return [gov for gov in f.read().strip().split(" ")]


def get_cores():
    return psutil.cpu_count()


def get_value_for_core(core, k):
    return get_value(ROOT + f"/cpu{core}/cpufreq/" + k)


def set_value_for_core(core, k, v):
    set_value(ROOT + f"/cpu{core}/cpufreq/" + k, v)


def set_value_for_all_cores(k, v):
    for i in range(get_cores()):
        set_value_for_core(i, k, v)


def set_governor(g):
    set_value_for_all_cores("scaling_governor", g)


def get_governor(core):
    return get_value_for_core(core, "scaling_governor")


def set_frequency(f, core=None):
    if core:
        set_value_for_core(core, "scaling_setspeed", f)
    else:
        set_value_for_all_cores("scaling_setspeed", f)


def get_frequency(core):
    return int(get_value_for_core(core, "scaling_cur_freq").strip())


def get_max_freq():
    return int(get_value(CPU0 + "/scaling_max_freq").strip())


def get_min_freq():
    return int(get_value(CPU0 + "/scaling_min_freq").strip())


def is_plugged():
    return int(get_value("/sys/class/power_supply/ADP1/online"))


def is_locked():
    return os.path.exists("/tmp/clockhead.lock")


minf, maxf = get_min_freq(), get_max_freq()
step = 300000
interval = 3


while True:
    if is_locked():
        print("Locked. Waiting ...")
        time.sleep(interval)
    elif is_plugged():
        if get_governor(0) != "performance":
            set_governor("performance")
        print("Plugged. Waiting ...")
        time.sleep(interval)
    else:
        if get_governor(0) != "userspace":
            set_governor("userspace")
        percs = psutil.cpu_percent(interval=interval, percpu=True)

        summary = {}

        for core, perc in enumerate(percs):
            cf = get_frequency(core)
            summary[core] = {}
            if perc > 90:
                if cf + 3*step < maxf:
                    set_frequency(cf + 3*step, core)
                    summary[core]["chg"] = "⬆️  ⬆️ "
                else:
                    set_frequency(maxf, core)
                    summary[core]["chg"] = "🔥"
            elif perc > 50:
                if cf + step < maxf:
                    set_frequency(cf + step, core)
                    summary[core]["chg"] = "⬆️ "
                else:
                    set_frequency(maxf, core)
                    summary[core]["chg"] = "🔥"
            if perc < 3:
                if cf - 2*step > minf:
                    set_frequency(cf - 2*step, core)
                    summary[core]["chg"] = "⬇️ ⬇️"
                else:
                    set_frequency(minf, core)
            elif perc < 10:
                if cf - step > minf:
                    set_frequency(cf - step, core)
                    summary[core]["chg"] = "⬇️"
                else:
                    set_frequency(minf, core)
            summary[core]["perc"] = perc
            summary[core]["freq"] = get_frequency(core)

        for core in summary:
            freq = summary[core]["freq"]
            perc = summary[core]["perc"]
            s = f"{core}:\t{perc}%, {freq/1e6:.2f}GHz"
            if "chg" in summary[core]:
                s += " " + summary[core]["chg"]
            print(s)

        print("")
