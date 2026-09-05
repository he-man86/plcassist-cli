# WHAT OF A TASK CAN ACTUALLY BE WRITTEN?
#
# `.task` is a read-only descriptor today (Type / Interval / Priority / Watchdog / Calls, rendered from the
# ScriptTaskObject facet). Making it read-WRITE is only worth designing if the vendor lets us set those back,
# and .NET reflection cannot answer that here: the scheduling members are IronPython EXTENSION members, absent
# from the type's property list, so GetProperty finds nothing while `task.priority` works fine.
#
# So this ASKS BY DOING: read each member, assign to it, read back, restore. A read-only member raises; a
# writable one does not - and reading back catches the third case, a write that is accepted and ignored.
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\A COPY.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-task-writable.py"
#
# POINT IT AT A COPY - it mutates the open project (it never saves, but do not risk an original).
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "task-writable.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def walk(node, depth=0):
    try:
        kids = list(node.get_children())
    except Exception:
        return
    for k in kids:
        yield k
        for x in walk(k, depth + 1):
            yield x

def probe_set(owner, name, newvalue, tag):
    label = tag + "." + name
    try:
        before = getattr(owner, name)
    except Exception:
        log("     %-26s ABSENT" % label); return
    try:
        setattr(owner, name, newvalue)
    except Exception:
        why = traceback.format_exc().strip().split(chr(10))[-1]
        log("     %-26s READ-ONLY  value=%r  %s" % (label, before, why[:80])); return
    try:
        after = getattr(owner, name)
    except Exception:
        after = "<unreadable>"
    took = "took" if str(after) != str(before) else "ACCEPTED BUT IGNORED"
    log("     %-26s WRITABLE   %r -> %r  (%s)" % (label, before, after, took))
    try:
        setattr(owner, name, before)
    except Exception:
        pass

try:
    import clr, System

    if not SRC or not os.path.exists(SRC):
        log("VOLT_PROBE_PROJECT not set or missing: %r" % SRC); raise SystemExit

    proj = projects.open(SRC)
    found = 0
    for node in walk(proj):
        try:
            name = str(node.get_name())
        except Exception:
            continue
        try:
            node.priority          # a task is a node that answers to the scheduling members
        except Exception:
            continue
        found += 1
        log("")
        log("=================== TASK %r ===================" % name)
        log("  read back: type=%r interval=%r %r priority=%r"
            % (node.kind_of_task, node.interval, node.interval_unit, node.priority))

        # Values chosen to DIFFER from what is there - writing a field its own value back reads as
        # "accepted but ignored" and says nothing. `priority` wants a STRING (an int raises TypeError,
        # which reads as read-only and is not).
        probe_set(node, "priority", "7", "task")
        probe_set(node, "interval", "50", "task")
        probe_set(node, "interval_unit", "s" if str(node.interval_unit) != "s" else "ms", "task")
        probe_set(node, "event", "someEvent", "task")

        try:
            wd = node.watchdog
            probe_set(wd, "enabled", not wd.enabled, "watchdog")
            probe_set(wd, "time", "99", "watchdog")
            probe_set(wd, "time_unit", "ms", "watchdog")
            probe_set(wd, "sensitivity", "3", "watchdog")
        except Exception:
            log("     watchdog                   ABSENT")

        try:
            pous = node.pous
            log("     task.pous                  %d entr(ies): %r  (add/insert/remove/replace)"
                % (len(list(pous)), [str(p) for p in pous]))
        except Exception:
            log("     task.pous                  ABSENT")

        if found >= 2:
            break
    if found == 0:
        log("no task object found (no node answered to .priority)")
    log("")
    log("done - the project was NOT saved")
except SystemExit:
    pass
except Exception:
    log(traceback.format_exc())
finally:
    f.close()
    try:
        import System; System.Environment.Exit(0)
    except Exception:
        pass
