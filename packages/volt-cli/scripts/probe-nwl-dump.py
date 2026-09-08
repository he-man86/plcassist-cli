# Dump the raw NWL item tree of NAMED POUs from a real project, member by member - the shape an
# adapter must actually read, rather than the shape its doubles were written to.
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\Some.project"; $env:VOLT_PROBE_POUS="ATD_FQI,SpeedCalculationDryer"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packagesolt-cli\scripts\probe-nwl-dump.py"
#
# The project is COPIED first and the original is never opened. Log next to this file (VOLT_PROBE_LOG
# overrides). ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7 and one non-ASCII byte is a
# SyntaxError before line 1 runs.
#
# This is the probe that settled the RETURN-coil bug: `out[0] = '???' type='BOOL' flags=Return` - the
# control-flow bit on the target OPERAND, which the readers lifted for Jump and not for Return.
import os
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-dump.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()





FLAGBITS = ("Negation", "Set", "Jump", "Return", "Rtrig", "Ftrig")
WANT = [w.strip() for w in (os.environ.get("VOLT_PROBE_POUS") or "").split(",") if w.strip()]

def flagstr(fl):
    if fl is None:
        return "-"
    on = [b for b in FLAGBITS if vp.prop(fl, b)]
    return "+".join(on) if on else "none"

def opdump(o):
    if o is None:
        return "<null>"
    return "%r type=%r flags=%s" % (vp.prop(o, "OperandExpr"), vp.prop(o, "Type"), flagstr(vp.prop(o, "Flags")))


try:
    import clr
    import System
    import shutil

    if not SRC or not os.path.exists(SRC):
        log("VOLT_PROBE_PROJECT not set or missing: %r" % SRC)
        raise SystemExit

    objmgr = None
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try:
            t = asm.GetType("_3S.CoDeSys.Core.SystemInstances")
        except Exception:
            t = None
        if t is None:
            continue
        p = t.GetProperty("ObjectMgr")
        if p is not None:
            objmgr = p.GetValue(None, None)
        if objmgr is not None:
            break
    if objmgr is None:
        log("ObjectMgr NOT reachable")
        raise SystemExit

    dst = os.path.join(tempfile.gettempdir(), "volt-nwl-dump.project")
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copyfile(SRC, dst)
    log("probe of: " + os.path.basename(SRC))
    log("wanted POUs: %r" % WANT)
    proj = projects.open(dst)                                    # noqa: F821
    log("opened (a copy; the original is never touched)")

    def visit(node, depth):
        if depth > 12:
            return
        try:
            kids = list(node.get_children())
        except Exception:
            return
        for k in kids:
            try:
                nm = str(k.get_name())
            except Exception:
                nm = "?"
            if nm in WANT:
                u = vp.unwrap(k)
                g = vp.prop(u, "guid")
                if g is not None:
                    try:
                        meta = objmgr.GetObjectToRead(vp.prop(u, "handle") or 0, g)
                        iobj = vp.prop(meta, "Object")
                        impl = vp.prop(iobj, "Implementation") if iobj is not None else None
                        nets = vp.prop(impl, "NetworkList") if impl is not None else None
                        if nets is not None:
                            log("")
                            log("=" * 78)
                            log("POU %s  (%d networks)" % (nm, len(nets)))
                            log("=" * 78)
                            for i in range(len(nets)):
                                net = nets[i]
                                log("")
                                log("-- NETWORK %d  title=%r label=%r comment=%r" %
                                    (i, vp.prop(net, "Title"), vp.prop(net, "Label"), vp.prop(net, "Comment")))
                                cnt = int(vp.prop(net, "NetworkItemCount") or 0)
                                for j in range(cnt):
                                    ok, tree = vp.call(net, "GetTree", [j])
                                    if ok and tree is not None:
                                        vp.dump(tree, 1, "tree[%d]" % j)
                    except Exception:
                        log("  !! " + traceback.format_exc())
            visit(k, depth + 1)

    visit(proj, 0)
    log("")
    log("done")
    proj.close()
except SystemExit:
    pass
except Exception:
    log(traceback.format_exc())
finally:
    f.close()
    try:
        import System
        System.Environment.Exit(0)
    except Exception:
        pass
