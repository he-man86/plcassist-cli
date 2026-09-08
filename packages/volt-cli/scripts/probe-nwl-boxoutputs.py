# Probe: can a BOX'S OUTPUT PINS be constructed, and what does the vendor fill in for us?
#
# The reader drops a box's own output pins today (`Box.Outputs` is only ever consulted for name
# collection, never written), so ~250 wired outputs in one real project vanish from the text. Before
# the format can carry them, the WRITE side has to be known: does a freshly created BoxTreeBox get its
# OutputParams from BoxType the way CallType is derived, are the output slots pre-created, and where
# does an appended operand land relative to the ENO slot?
#
# Works on a COPY of the committed fixture project. ASCII ONLY (IronPython 2.7).
import os
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.join(HERE, "..", "test")

LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-boxoutputs.log")
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


try:
    import clr
    import System
    import shutil

    objmgr = None
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try: t = asm.GetType("_3S.CoDeSys.Core.SystemInstances")
        except Exception: t = None
        if t is None: continue
        p = t.GetProperty("ObjectMgr")
        if p is not None: objmgr = p.GetValue(None, None)
        if objmgr is not None: break
    if objmgr is None:
        log("ObjectMgr NOT reachable"); raise SystemExit

    SRC = os.path.join(TEST, "fixtures", "CodesysTestProject.project")
    dst = os.path.join(tempfile.gettempdir(), "volt-nwl-boxoutputs.project")
    if os.path.exists(dst): os.remove(dst)
    shutil.copyfile(SRC, dst)
    proj = projects.open(dst)
    app = find(proj, "Application")

    L = getattr(ImplementationLanguages, "fbd")
    pou = app.create_pou(name="VLT_BOXOUT", type=PouType.FunctionBlock, language=L)
    pou.textual_declaration.replace(
        "FUNCTION_BLOCK VLT_BOXOUT\nVAR\n  src : INT;\n  dst : INT;\n  rung : BOOL;\nEND_VAR")
    node = vp.unwrap(pou)
    h = vp.prop(node, "handle") or 0
    g = vp.prop(node, "guid")

    meta = objmgr.GetObjectToModify(h, g)
    impl = vp.prop(vp.prop(meta, "Object"), "Implementation")
    nets = vp.prop(impl, "NetworkList")
    plug = nets[0].GetType().Assembly

    T = {}
    for t in plug.GetTypes():
        if t.Name in ("BoxTreeBox", "BoxTreeOperand", "Operand", "Flags"):
            T[t.Name] = t
    log("types: %r" % sorted(T.keys()))

    def dump_box(b, label):
        log("  -- %s" % label)
        log("     BoxType   = %r" % vp.prop(b, "BoxType"))
        log("     CallType  = %r" % vp.prop(b, "CallType"))
        log("     EnEno     = %r   En = %r" % (vp.prop(b, "EnEno"), vp.prop(b, "En")))
        ip = vp.prop(b, "InputParams")
        op = vp.prop(b, "OutputParams")
        def names(pl):
            if pl is None: return None
            try: return [str(x) for x in (vp.prop(pl, "Names") or [])]
            except Exception: return "<threw>"
        log("     InputParams.Names  = %r" % names(ip))
        log("     OutputParams.Names = %r" % names(op))
        try: ii = len(list(vp.prop(b, "InputItemList") or []))
        except Exception: ii = "<threw>"
        log("     InputItemList count = %r" % ii)
        outs = vp.prop(b, "Outputs")
        lst = vp.prop(outs, "List") if outs is not None else None
        log("     Outputs.List = %r" % (None if lst is None else
            [None if x is None else vp.prop(x, "OperandExpr") for x in lst],))

    log("")
    log("=== 1. a bare BoxTreeBox, before BoxType ===")
    box = System.Activator.CreateInstance(T["BoxTreeBox"], System.Array[System.Object]([]))
    dump_box(box, "fresh")

    log("")
    log("=== 2. after BoxType = MOVE (does the vendor derive the pins?) ===")
    box.GetType().GetProperty("BoxType", vp.bf()).SetValue(box, "MOVE", None)
    dump_box(box, "BoxType=MOVE")

    log("")
    log("=== 3. append an INPUT, then an OUTPUT operand ===")
    src_op = System.Activator.CreateInstance(T["Operand"], System.Array[System.Object](["src"]))
    dst_op = System.Activator.CreateInstance(T["Operand"], System.Array[System.Object](["dst"]))
    bto = System.Activator.CreateInstance(T["BoxTreeOperand"], System.Array[System.Object]([src_op]))
    ok, res = vp.call(box, "AppendInputItem", [bto])
    log("  AppendInputItem(src) -> %s %s" % (ok, "" if ok else res))
    outs = vp.prop(box, "Outputs")
    ok, res = vp.call(outs, "AppendOutputItem", [dst_op])
    log("  Outputs.AppendOutputItem(dst) -> %s %s" % (ok, "" if ok else res))
    dump_box(box, "after appends")

    log("")
    log("=== 4. append to the network and ask the vendor if it is valid ===")
    net0 = nets[0]
    validity(net0, "before")
    ok, res = vp.call(net0, "AppendTree", [box])
    log("  AppendTree -> %s %s" % (ok, "" if ok else res))
    validity(net0, "after append")
    objmgr.SetObject(meta, True, None)
    log("  committed")

    log("")
    log("=== 5. reload and read it back ===")
    proj.save()
    proj.close()
    proj = projects.open(dst)
    pou2 = find(proj, "VLT_BOXOUT")
    n2 = vp.unwrap(pou2)
    meta2 = objmgr.GetObjectToRead(vp.prop(n2, "handle") or 0, vp.prop(n2, "guid"))
    impl2 = vp.prop(vp.prop(meta2, "Object"), "Implementation")
    nets2 = vp.prop(impl2, "NetworkList")
    cnt = int(vp.prop(nets2[0], "NetworkItemCount") or 0)
    log("  network item count = %d" % cnt)
    for j in range(cnt):
        ok, tree = vp.call(nets2[0], "GetTree", [j])
        if ok and tree is not None:
            log("  tree[%d]: %s" % (j, tree.GetType().Name))
            if tree.GetType().Name == "BoxTreeBox":
                dump_box(tree, "read back")
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
