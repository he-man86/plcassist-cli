# CAN A TASK BE CREATED AND REMOVED through the scripting API, and with what call?
#
# Making `.task` read-write has to cover a task being ADDED or DELETED in the workspace, not just edited. Delete
# is the generic `remove()` every ScriptObject has; CREATE needs a task-config call, and this finds its exact
# signature by reflecting the type (these are real .NET members, unlike the IronPython extension members that
# carry a task's scheduling fields - see probe-task-writable.py).
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\A COPY.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-task-create.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "task-create.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def sig(m):
    return "%s(%s) -> %s" % (m.Name, ", ".join([p.ParameterType.Name + " " + p.Name for p in m.GetParameters()]),
                             m.ReturnType.Name)

try:
    import clr, System
    BF = (System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic |
          System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static)

    for want in ("ScriptTaskConfigObject", "ScriptTaskObject", "ScriptPouObjectList", "ScriptWatchdog"):
        found = None
        for asm in System.AppDomain.CurrentDomain.GetAssemblies():
            try:
                t = asm.GetType("_3S.CoDeSys.ScriptDriverProjects." + want)
            except Exception:
                t = None
            if t is not None:
                found = t
                break
        log("")
        log("=== %s : %s" % (want, "FOUND" if found is not None else "not found"))
        if found is None:
            continue
        for m in sorted(found.GetMethods(BF), key=lambda x: x.Name):
            if m.Name.startswith("get_") or m.Name.startswith("set_"):
                continue
            if m.Name in ("Equals", "Finalize", "GetHashCode", "GetType", "MemberwiseClone", "ToString"):
                continue
            log("    " + sig(m))
        for p in sorted(found.GetProperties(BF), key=lambda x: x.Name):
            log("    prop %-24s %-26s get=%s set=%s" % (p.Name, p.PropertyType.Name, p.CanRead, p.CanWrite))

    # And the IronPython extension surface on a live task-config node, which reflection cannot see.
    if SRC and os.path.exists(SRC):
        proj = projects.open(SRC)
        def walk(n, d=0):
            try:
                kids = list(n.get_children())
            except Exception:
                return
            for k in kids:
                yield k
                for x in walk(k, d + 1):
                    yield x
        for node in walk(proj):
            try:
                nm = str(node.get_name())
            except Exception:
                continue
            if nm != "Task Configuration":
                continue
            log("")
            log("=== live 'Task Configuration' node: %s" % node.GetType().FullName)
            names = []
            for attr in dir(node):
                if attr.startswith("_"):
                    continue
                names.append(attr)
            log("    dir(): %s" % ", ".join(sorted(names)))
            break
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
