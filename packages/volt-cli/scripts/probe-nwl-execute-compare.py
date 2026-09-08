# Put a CREATED Execute box next to a REAL one, member for member.
#
# Volt can now create one that reloads and round-trips byte-identically, and the BUILD still answers
# "Expression expected instead of '?'". So the box differs from the vendor's in something neither the
# reader nor the text can see. This dumps every property of both.
#
# VOLT_REAL_PROJECT  a project containing an engineer-drawn Execute box (default: none, skips that half)
# ASCII ONLY - IronPython 2.7.
import os
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.join(HERE, "..", "test")

LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-execute-compare.log")
f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()





def seq(o):
    """A vendor collection as a python list, via reflection (they are not IronPython-iterable)."""
    if o is None:
        return None
    n = vp.prop(o, "Count")
    if n is None:
        return None
    out = []
    t = o.GetType()
    for src in [t] + list(t.GetInterfaces()):
        p = src.GetProperty("Item")
        if p is not None:
            for i in range(int(n)):
                try:
                    out.append(p.GetValue(o, [i]))
                except Exception:
                    return out
            return out
    return out

def find(root, want, depth=0):
    if depth > 9:
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

def validity(net, tag):
    log("  %-22s FBDValid=%s ILValid=%s ILActive=%s items=%s"
        % (tag, vp.prop(net, "FBDValid"), vp.prop(net, "ILValid"),
           vp.prop(net, "ILActive"), vp.prop(net, "NetworkItemCount")))




ST = "iCount := iCount + 1;"
REAL = os.environ.get("VOLT_REAL_PROJECT") or ""
REAL_POU = os.environ.get("VOLT_REAL_POU") or "SpeedCalculationDryer"

def dump_all(o, label):
    log("  %s : %s" % (label, o.GetType().FullName))
    ins = vp.prop(o, "Instance")
    if ins is not None:
        log("      >> Instance.OperandExpr = %r   Type=%r   IsInstance=%r"
            % (vp.prop(ins, "OperandExpr"), vp.prop(ins, "Type"), vp.prop(ins, "IsInstance")))
    seen = set()
    for src2 in [o.GetType()] + list(o.GetType().GetInterfaces()):
        for pr in src2.GetProperties():
            if pr.Name in seen: continue
            seen.add(pr.Name)
            try: v = pr.GetValue(o, None)
            except Exception: v = "<threw>"
            sv = repr(v)
            if len(sv) > 110: sv = sv[:110] + "..."
            log("      %-28s = %s" % (pr.Name, sv))

def find_execute(nets):
    for i in range(len(nets)):
        cnt = int(vp.prop(nets[i], "NetworkItemCount") or 0)
        for j in range(cnt):
            ok, tree = vp.call(nets[i], "GetTree", [j])
            if ok and tree is not None and str(vp.prop(tree, "BoxType") or "") == "EXECUTE":
                return tree
    return None

try:
    import clr, System, shutil

    objmgr = None
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try: t = asm.GetType("_3S.CoDeSys.Core.SystemInstances")
        except Exception: t = None
        if t is None: continue
        p = t.GetProperty("ObjectMgr")
        if p is not None: objmgr = p.GetValue(None, None)
        if objmgr is not None: break

    # ---- the CREATED one -----------------------------------------------------------------
    SRC = os.path.join(TEST, "fixtures", "CodesysTestProject.project")
    dst = os.path.join(tempfile.gettempdir(), "volt-exec-compare.project")
    if os.path.exists(dst): os.remove(dst)
    shutil.copyfile(SRC, dst)
    proj = projects.open(dst)
    app = find(proj, "Application")
    pou = app.create_pou(name="VLT_CMP", type=PouType.FunctionBlock, language=getattr(ImplementationLanguages, "fbd"))
    pou.textual_declaration.replace("FUNCTION_BLOCK VLT_CMP\nVAR\n  iCount : INT;\nEND_VAR")
    node = vp.unwrap(pou)
    meta = objmgr.GetObjectToModify(vp.prop(node, "handle") or 0, vp.prop(node, "guid"))
    impl = vp.prop(vp.prop(meta, "Object"), "Implementation")
    nets = vp.prop(impl, "NetworkList")
    plug = nets[0].GetType().Assembly
    T = {}
    for t in plug.GetTypes(): T[t.Name] = t
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try: tt = asm.GetType("_3S.CoDeSys.STObject.STImplementationObject")
        except Exception: tt = None
        if tt is not None: T["STImplementationObject"] = tt; break

    box = System.Activator.CreateInstance(T["BoxTreeBox"], System.Array[System.Object]([]))
    box.GetType().GetProperty("BoxType", vp.bf()).SetValue(box, "EXECUTE", None)
    snip = System.Activator.CreateInstance(T["STSnippet"], System.Array[System.Object]([]))
    sti = System.Activator.CreateInstance(T["STImplementationObject"], System.Array[System.Object]([]))
    for src3 in [snip.GetType()] + list(snip.GetType().GetInterfaces()):
        for pr in src3.GetProperties():
            if pr.Name.endswith("Snippet") and pr.CanWrite:
                pr.SetValue(snip, sti, None)
    td = vp.prop(sti, "TextDocument")
    try: vp.call(td, "Insert", [0, ST])
    except Exception: pass
    log("created snippet text = %r" % (vp.prop(td, "Text"),))
    box.GetType().GetProperty("STSnippet", vp.bf()).SetValue(box, snip, None)
    vp.call(nets[0], "AppendTree", [box])
    objmgr.SetObject(meta, True, None)
    proj.save()
    proj.close()

    proj = projects.open(dst)
    n2 = vp.unwrap(find(proj, "VLT_CMP"))
    meta2 = objmgr.GetObjectToRead(vp.prop(n2, "handle") or 0, vp.prop(n2, "guid"))
    nets2 = vp.prop(vp.prop(vp.prop(meta2, "Object"), "Implementation"), "NetworkList")
    made = find_execute(nets2)
    log("")
    log("=" * 70)
    log("CREATED Execute box")
    log("=" * 70)
    if made is None: log("  <none found>")
    else: dump_all(made, "box")
    proj.close()

    # ---- the REAL one --------------------------------------------------------------------
    if REAL and os.path.exists(REAL):
        rdst = os.path.join(tempfile.gettempdir(), "volt-exec-compare-real.project")
        if os.path.exists(rdst): os.remove(rdst)
        shutil.copyfile(REAL, rdst)
        proj = projects.open(rdst)
        target = [None]
        def visit(n, d):
            if d > 12 or target[0] is not None: return
            try: kids = list(n.get_children())
            except Exception: return
            for k in kids:
                try: nm = str(k.get_name())
                except Exception: nm = "?"
                if nm == REAL_POU: target[0] = k; return
                visit(k, d + 1)
        visit(proj, 0)
        log("")
        log("=" * 70)
        log("REAL Execute box (%s)" % REAL_POU)
        log("=" * 70)
        if target[0] is None:
            log("  <POU not found>")
        else:
            u = vp.unwrap(target[0])
            m3 = objmgr.GetObjectToRead(vp.prop(u, "handle") or 0, vp.prop(u, "guid"))
            nets3 = vp.prop(vp.prop(vp.prop(m3, "Object"), "Implementation"), "NetworkList")
            real = find_execute(nets3)
            if real is None: log("  <no EXECUTE box>")
            else: dump_all(real, "box")
        proj.close()
    log("")
    log("done")
except SystemExit:
    pass
except Exception:
    log(traceback.format_exc())
finally:
    f.close()
    try:
        import System; System.Environment.Exit(0)
    except Exception: pass
