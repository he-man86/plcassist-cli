# DOES THE TASK CONFIGURATION SURVIVE DELETING ITS LAST TASK?
#
# `corpus-migration.ts` empties the blank target in its own push, which deletes the template's `MainTask`, and the
# very next push's first task CREATE fails with "node has no ScriptTaskConfigObject facet". Two shapes explain
# that and they need opposite fixes: either the vendor REMOVES the Task Configuration when its last child goes
# (Volt must recreate it), or the container is still there and `TreeNav.DescendOrCreateFolder` simply made a plain
# folder beside it (Volt must stop doing that). Measure, do not guess.
#
#   pwsh> & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI `
#           --runscript="<repo>\packages\volt-cli\scripts\probe-task-config-survives-delete.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import shutil
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "task-config-survives-delete.log")
TEMPLATE = r"C:\Program Files\CODESYS 3.5.21.40\CODESYS\Templates\Standard.project"

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def facets(node):
    out = []
    try:
        for x in node.Extender.Extensions:
            out.append(x.GetType().Name)
    except Exception:
        out.append("<no Extender.Extensions>")
    return out

def survey(proj, when):
    log("")
    log("=== %s" % when)
    def walk(n, d=0):
        try:
            kids = list(n.get_children())
        except Exception:
            return
        for k in kids:
            try:
                nm = str(k.get_name())
            except Exception:
                nm = "<unnamed>"
            log("%s%s   [%s]  facets=%s" % ("  " * d, nm, k.GetType().Name, ",".join(facets(k))))
            walk(k, d + 1)
    walk(proj)

try:
    scratch = os.path.join(os.environ.get("TEMP", HERE), "volt-probe-taskcfg.project")
    if os.path.exists(scratch):
        os.remove(scratch)
    shutil.copyfile(TEMPLATE, scratch)
    proj = projects.open(scratch)

    survey(proj, "BEFORE - the shipped template")

    def find(n, name):
        for k in n.get_children():
            if str(k.get_name()) == name:
                return k
            hit = find(k, name)
            if hit is not None:
                return hit
        return None

    task = find(proj, "MainTask")
    log("")
    log("MainTask found: %s" % (task is not None))
    if task is not None:
        task.remove()
        log("MainTask.remove() returned")

    survey(proj, "AFTER - the last task deleted")

    cfg = find(proj, "Task Configuration")
    log("")
    log("Task Configuration still present: %s" % (cfg is not None))
    if cfg is not None:
        log("  facets: %s" % ",".join(facets(cfg)))
        try:
            made = cfg.create_task("VltProbeTask")
            log("  create_task after the delete: OK -> %s" % str(made.get_name()))
        except Exception:
            log("  create_task after the delete FAILED:\n%s" % traceback.format_exc())

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
