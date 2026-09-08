# CAN A TASK'S KIND BE WRITTEN?
#
# `.task` carries `Type: Cyclic` and `WriteTask` writes everything on that file EXCEPT the type, so a cyclic
# task migrated into a blank project came back `Freewheeling` - measured by `scripts/corpus-migration.ts` on
# pro2193's `EdgePcTask`. The read side takes it from `kind_of_task` (CodesysObjectModel.ReadTask); whether that
# member can be ASSIGNED is not answerable by reflection, because the scheduling members are IronPython
# extension members and absent from the type's property list. So ask by doing, exactly as
# probe-task-writable.py does for priority/interval: read, assign, read back, restore.
#
# The value's TYPE is the open question. `kind_of_task` reads back as something that str()s to "Cyclic"; this
# tries the string, the enum object taken off another task, and the underlying int, and reports which one takes.
#
#   pwsh> & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI `
#           --runscript="<repo>\packages\volt-cli\scripts\probe-task-kind.py"
#
# It works on a COPY of the shipped Standard template - never an engineer's project - and never saves.
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import shutil
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "task-kind.log")
TEMPLATE = r"C:\Program Files\CODESYS 3.5.21.40\CODESYS\Templates\Standard.project"

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def find(node, name):
    for k in node.get_children():
        if str(k.get_name()) == name:
            return k
        hit = find(k, name)
        if hit is not None:
            return hit
    return None

def try_set(task, value, label):
    before = task.kind_of_task
    try:
        task.kind_of_task = value
    except Exception:
        log("    %-26s RAISED %s" % (label, traceback.format_exc().strip().splitlines()[-1]))
        return
    after = task.kind_of_task
    took = str(after) != str(before)
    log("    %-26s accepted, read back %r (%s)" % (label, str(after), "CHANGED" if took else "IGNORED"))
    try:
        task.kind_of_task = before
    except Exception:
        pass

try:
    scratch = os.path.join(os.environ.get("TEMP", HERE), "volt-probe-taskkind.project")
    if os.path.exists(scratch):
        os.remove(scratch)
    shutil.copyfile(TEMPLATE, scratch)
    proj = projects.open(scratch)

    task = find(proj, "MainTask")
    if task is None:
        log("no MainTask in the template")
    else:
        current = task.kind_of_task
        log("kind_of_task reads %r  (python type %s, .NET type %s)"
            % (str(current), type(current).__name__,
               current.GetType().FullName if hasattr(current, "GetType") else "n/a"))

        # What are the legal values? The enum type itself is the authority, not a guess at the spelling.
        try:
            import System
            t = current.GetType()
            log("enum values: %s" % ", ".join([str(v) for v in System.Enum.GetValues(t)]))
        except Exception:
            log("not a .NET enum: %s" % traceback.format_exc().strip().splitlines()[-1])

        log("  writes:")
        try_set(task, "Freewheeling", "string 'Freewheeling'")
        try_set(task, 1, "int 1")
        try:
            import System
            t = current.GetType()
            for v in System.Enum.GetValues(t):
                if str(v) != str(current):
                    try_set(task, v, "enum %s" % str(v))
                    break
        except Exception:
            pass

    log("")
    log("done")
except Exception:
    log(traceback.format_exc())
finally:
    f.close()
    try:
        import System; System.Environment.Exit(0)
    except Exception:
        pass
