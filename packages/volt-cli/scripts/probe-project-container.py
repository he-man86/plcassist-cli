# What can CREATE a top-level object at the PROJECT ROOT (the POU pool), rather than under the Application?
#
# `CodesysObjectModel.Container` constructs ScriptIecLanguageObjectContainerObject over the parent's
# ScriptObject, and that constructor REFUSES the project object ("Constructor on type
# '_3S.CoDeSys.ScriptDriverProjects.ScriptIecLanguageObjectContainerObject' not found") - so an item the walk
# emits at the tree root cannot be pushed back there. This dumps the project object's own type/interfaces and
# every ScriptIecLanguage* constructor, so the right container is MEASURED rather than guessed.
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\Some.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-project-container.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "project-container.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()


try:
    import clr
    import System

    if not SRC or not os.path.exists(SRC):
        log("VOLT_PROBE_PROJECT not set or missing: %r" % SRC); raise SystemExit

    proj = projects.open(SRC)
    log("project  : %s" % proj.GetType().FullName)
    base = vp.unwrap(proj)
    log("unwrapped: %s" % (base.GetType().FullName if base is not None else None))
    if base is not None:
        for i in base.GetType().GetInterfaces():
            log("   iface : %s" % i.FullName)

    # The Application, for contrast - this one the container DOES accept today.
    def find(root, want, depth=0):
        if depth > 6:
            return None
        try:
            kids = list(root.get_children())
        except Exception:
            return None
        for k in kids:
            try:
                if str(k.get_name()) == want:
                    return k
            except Exception:
                pass
            r = find(k, want, depth + 1)
            if r is not None:
                return r
        return None

    app = find(proj, "Application")
    appbase = vp.unwrap(app)
    log("")
    log("Application unwrapped: %s" % (appbase.GetType().FullName if appbase is not None else None))
    if appbase is not None:
        for i in appbase.GetType().GetInterfaces():
            log("   iface : %s" % i.FullName)

    log("")
    log("-- ScriptDriverProjects containers and their constructors --")
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try:
            types = asm.GetTypes()
        except Exception:
            continue
        for t in types:
            n = t.FullName or ""
            if not n.startswith("_3S.CoDeSys.ScriptDriverProjects."):
                continue
            if "Container" not in n and "Project" not in n:
                continue
            ctors = t.GetConstructors(
                System.Reflection.BindingFlags.Instance |
                System.Reflection.BindingFlags.Public |
                System.Reflection.BindingFlags.NonPublic)
            for c in ctors:
                ps = ", ".join([p.ParameterType.Name + " " + p.Name for p in c.GetParameters()])
                log("%s(%s)" % (n, ps))

    log("")
    log("-- create_* methods reachable on the project object itself --")
    for src in [proj, base]:
        if src is None:
            continue
        log("on %s:" % src.GetType().FullName)
        seen = set()
        for m in src.GetType().GetMethods():
            if m.Name.startswith("create_") and m.Name not in seen:
                seen.add(m.Name)
                log("   %s(%s)" % (m.Name, ", ".join([p.ParameterType.Name for p in m.GetParameters()])))

    log("done")
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
