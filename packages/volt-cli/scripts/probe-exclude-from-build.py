# Is an object EXCLUDED FROM BUILD, and can the bridge read that?
#
# WHAT THIS ESTABLISHED (2026-09-05, live SP21):
#   * `_3S.CoDeSys.ScriptDriverProjects.ScriptBuildProperties` EXISTS and carries exactly the members needed -
#     `exclude_from_build` / `exclude_from_build_is_valid` (plus external / link_always / enable_system_call).
#   * Its constructors take a concrete `ScriptObject` (also on the nested `Readable` / `Modifyable` views), the
#     same construct-over-the-base shape the IEC language containers use.
#
# WHAT IS STILL OPEN: reaching it from a --runscript. The tree walk hands back an
# `ExtendedObject<IScriptObject>` whose reported .GetType() says `ScriptObject` and which no constructor
# accepts, and the object exposes no `build` member either. The C# driver unwraps differently
# (CodesysObjectModel.Unwrap) and is the likelier place to make this work.
#
# WHY IT MATTERS: `Lenze_MID-S100` builds with ZERO errors while `Mach1_MIDS` and `AHWF` - both LIVE by Volt's
# reachability - hold four `???` assignment targets. That shape IS a compile error when the object is compiled
# (measured twice through scripts/audit-check.ts in the fixture project), so CODESYS is not compiling those two.
# Exclude-from-build is the leading explanation and Volt has no way to see it: the wire carries no such flag, so
# the LSP reports four errors the build never will. (`POU` is NOT this case - it is dead code, and the LSP's
# task-root dead-POU suppression already silences its four `???` correctly.)
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\Some.project"; $env:VOLT_PROBE_POUS="POU,Mach1_MIDS"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packagesolt-cli\scripts\probe-exclude-from-build.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "exclude-from-build.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""
WANT = [w.strip() for w in (os.environ.get("VOLT_PROBE_POUS") or "").split(",") if w.strip()]

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

BF = None
def _bf():
    global BF
    if BF is None:
        from System.Reflection import BindingFlags as B
        BF = B.Public | B.NonPublic | B.Instance | B.FlattenHierarchy
    return BF

def unwrap(o):
    for _ in range(10):
        if o is None:
            return None
        try:
            bp = o.GetType().GetProperty("BaseObject", _bf())
        except Exception:
            return o
        if bp is None:
            return o
        try:
            inner = bp.GetValue(o, None)
        except Exception:
            return o
        if inner is None or inner is o:
            return o
        o = inner
    return o

def walk(node, depth=0):
    try:
        kids = list(node.get_children())
    except Exception:
        return
    for k in kids:
        try:
            nm = str(k.get_name())
        except Exception:
            nm = "<?>"
        yield nm, k
        for x in walk(k, depth + 1):
            yield x

try:
    import clr
    import System

    if not SRC or not os.path.exists(SRC):
        log("VOLT_PROBE_PROJECT not set or missing: %r" % SRC); raise SystemExit

    proj = projects.open(SRC)

    bp_type = None
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try:
            t = asm.GetType("_3S.CoDeSys.ScriptDriverProjects.ScriptBuildProperties")
        except Exception:
            t = None
        if t is not None:
            bp_type = t
            break
    log("ScriptBuildProperties type: %s" % (bp_type.FullName if bp_type is not None else None))
    if bp_type is not None:
        log("  members: %s" % ", ".join(sorted(set(p.Name for p in bp_type.GetProperties(_bf())))))

    def build_props(obj):
        """ScriptBuildProperties over the object's ScriptObject - the same construct-over-the-base pattern the
        IEC language containers use (CodesysObjectModel.Container). There is no `build` member on ScriptObject;
        the readable view is a nested type taking the base object."""
        if bp_type is None:
            return None
        # The ctor wants the CONCRETE ScriptObject. `obj` from the tree walk is an
        # ExtendedObject<IScriptObject> wrapper whose reported .GetType() lies, so try every rung of the
        # BaseObject chain rather than trusting one - the same reason CodesysObjectModel.Unwrap loops.
        rungs = []
        cur = obj
        for _ in range(6):
            if cur is None or cur in rungs:
                break
            rungs.append(cur)
            try:
                bpp = cur.GetType().GetProperty("BaseObject", _bf())
                cur = bpp.GetValue(cur, None) if bpp is not None else None
            except Exception:
                cur = None
        cands = [bp_type] + [t for t in bp_type.GetNestedTypes(_bf()) if t.Name in ("Readable", "Modifyable")]
        for rung in rungs:
            for t in cands:
                for c in t.GetConstructors(_bf()):
                    ps = c.GetParameters()
                    if len(ps) != 1:
                        continue
                    try:
                        return c.Invoke(System.Array[System.Object]([rung]))
                    except Exception:
                        pass
        log("      no ctor accepted any of %d BaseObject rung(s)" % len(rungs))
        return None

    for nm, node in walk(proj):
        if WANT and nm not in WANT:
            continue
        log("")
        log("-- %s" % nm)
        b = build_props(node)
        if b is None:
            log("   no `build` accessor on %s" % node.GetType().FullName)
            continue
        log("   build props: %s" % b.GetType().FullName)
        for p in sorted(b.GetType().GetProperties(_bf()), key=lambda x: x.Name):
            try:
                val = p.GetValue(b, None)
            except Exception:
                val = "<threw>"
            log("      %-28s = %r" % (p.Name, val))

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
