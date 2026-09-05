# HOW IS A TASK'S CALL LIST MUTATED?
#
# `ScriptPouObjectList` advertises add/insert/remove/replace, and calling `remove(index)` straight on the live
# list answers "Cannot remove the specified item because it was not found in the specified Collection." Both
# ScriptTaskObject and ScriptPouObjectList also expose `PerformWithWriteableCopy(Action<T>)`, which reads like
# the vendor saying the object handed out is a READ-ONLY view. This tries both and reports which one lands.
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\A COPY.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-task-calllist.py"
#
# POINT IT AT A COPY - it mutates the open project (never saves).
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "task-calllist.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def why():
    return traceback.format_exc().strip().split(chr(10))[-1][:130]

def names(pous):
    try:
        return [str(p) for p in pous]
    except Exception:
        return "<unreadable>"

def walk(node, depth=0):
    try:
        kids = list(node.get_children())
    except Exception:
        return
    for k in kids:
        yield k
        for x in walk(k, depth + 1):
            yield x

try:
    import clr, System

    if not SRC or not os.path.exists(SRC):
        log("VOLT_PROBE_PROJECT not set or missing: %r" % SRC); raise SystemExit

    proj = projects.open(SRC)
    for node in walk(proj):
        try:
            node.priority
        except Exception:
            continue
        name = str(node.get_name())
        log("")
        log("=================== TASK %r ===================" % name)
        log("  before: %r" % names(node.pous))

        # 1. straight at the live list
        try:
            node.pous.remove(0)
            log("  DIRECT remove(0)                 OK   -> %r" % names(node.pous))
        except Exception:
            log("  DIRECT remove(0)                 FAILS: %s" % why())

        # 2. by NAME - `remove(0)` turns out to be remove-by-VALUE, not remove-at-index
        try:
            first = names(node.pous)[0]
            node.pous.remove(first)
            log("  remove(name=%r)%s OK   -> %r" % (first, " " * max(1, 18 - len(first)), names(node.pous)))
        except Exception:
            log("  remove(by name)                  FAILS: %s" % why())

        # 3. and an ADD, both ways, since a rebuild needs both halves
        try:
            node.pous.add("PLC_PRG", "")
            log("  DIRECT add                       OK   -> %r" % names(node.pous))
        except Exception:
            log("  DIRECT add                       FAILS: %s" % why())

        # and emptying it completely, which is what a rebuild does first
        try:
            while len(names(node.pous)) > 0:
                node.pous.remove(names(node.pous)[0])
            log("  drain by name                    OK   -> %r" % names(node.pous))
        except Exception:
            log("  drain by name                    FAILS: %s" % why())

        break
    log("")
    log("done - NOT saved")
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
