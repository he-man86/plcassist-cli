# CORRELATE the NWL coil flag-bits with the vendor's OWN name for each coil kind.
#
# `IFlags` has Negation and Set and no Reset, so what a RESET coil looks like in the model is not
# something to infer from the logic around it. CODESYS's PLCopen export spells coil storage outright
# (`<coil negated=".." storage="set|reset|none">`), so exporting every POU that has a coil and pairing
# the two views per POU is the vendor answering in its own words.
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-coils.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()





FLAGBITS = ("Negation", "Set", "Jump", "Return", "Rtrig", "Ftrig")

def combo(fl):
    if fl is None:
        return "none"
    on = [b for b in FLAGBITS if vp.prop(fl, b)]
    return "+".join(on) if on else "none"

try:
    import clr, System, shutil, re
    if not SRC or not os.path.exists(SRC):
        log("VOLT_PROBE_PROJECT missing: %r" % SRC); raise SystemExit
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

    dst = os.path.join(tempfile.gettempdir(), "volt-nwl-coils.project")
    if os.path.exists(dst): os.remove(dst)
    shutil.copyfile(SRC, dst)
    proj = projects.open(dst)
    log("opened a copy of " + os.path.basename(SRC))

    # ---- side A: every assignment TARGET's flag combo, per POU -------------------------------
    coils = {}          # pou -> {combo: count}
    objs = {}           # pou -> scripting object

    def note(pou, c):
        coils.setdefault(pou, {})
        coils[pou][c] = coils[pou].get(c, 0) + 1

    def walk(n, pou):
        if n is None: return
        tn = n.GetType().Name
        if tn == "BoxTreeAssign":
            outs = vp.prop(n, "Outputs")
            lst = vp.prop(outs, "List") if outs is not None else None
            if lst is not None:
                for x in lst:
                    if x is not None:
                        note(pou, combo(vp.prop(x, "Flags")))
        for single in ("RValue", "Input", "Merger", "Operand"):
            c = vp.prop(n, single)
            if c is not None: walk(c, pou)
        for coll in ("InputItemList", "Trees"):
            c = vp.prop(n, coll)
            if c is not None:
                try:
                    for x in c: walk(x, pou)
                except Exception: pass

    def visit(node, depth):
        if depth > 12: return
        try: kids = list(node.get_children())
        except Exception: return
        for k in kids:
            try: nm = str(k.get_name())
            except Exception: nm = "?"
            u = vp.unwrap(k); g = vp.prop(u, "guid")
            if g is not None:
                try:
                    meta = objmgr.GetObjectToRead(vp.prop(u, "handle") or 0, g)
                    iobj = vp.prop(meta, "Object")
                    impl = vp.prop(iobj, "Implementation") if iobj is not None else None
                    nl = vp.prop(impl, "NetworkList") if impl is not None else None
                    if nl is not None:
                        objs[nm] = k
                        for i in range(len(nl)):
                            net = nl[i]
                            cnt = int(vp.prop(net, "NetworkItemCount") or 0)
                            for j in range(cnt):
                                ok, tree = vp.call(net, "GetTree", [j])
                                if ok and tree is not None:
                                    walk(tree, nm)
                except Exception:
                    pass
            visit(k, depth + 1)
    visit(proj, 0)

    # ---- side B: the vendor's own word, for every POU that has a non-plain coil --------------
    interesting = sorted([p for p, d in coils.items() if any(c != "none" for c in d)])
    log("POUs with a non-plain coil: %d" % len(interesting))
    log("")
    log("%-28s %-34s %s" % ("POU", "NWL target flags", "PLCopen <coil negated/storage>"))
    log("-" * 110)
    for pou in interesting:
        obj = objs.get(pou)
        nwl = ", ".join("%s x%d" % (c, n) for c, n in sorted(coils[pou].items()))
        out = os.path.join(tempfile.gettempdir(), "volt-coilx-%s.xml" % re.sub(r"[^A-Za-z0-9_]", "_", pou))
        plc = "<export failed>"
        try:
            if os.path.exists(out):
                os.remove(out)
        except Exception:
            out = out + "2"
        try:
            proj.export_xml([obj], out)
            xml = open(out, "rb").read().decode("utf-8", "replace")
            seen = {}
            for m in re.finditer(r'<coil\b[^>]*negated="(\w+)"[^>]*storage="(\w+)"', xml):
                key = "neg=%s/%s" % m.groups()
                seen[key] = seen.get(key, 0) + 1
            plc = ", ".join("%s x%d" % (k, v) for k, v in sorted(seen.items())) or "<no coils>"
        except Exception:
            plc = "<export threw: %s>" % traceback.format_exc().splitlines()[-1][:60]
        log("%-28s %-34s %s" % (pou[:28], nwl[:34], plc))
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
