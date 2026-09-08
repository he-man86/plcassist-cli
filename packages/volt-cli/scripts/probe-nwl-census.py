# Census the NWL box contract across EVERY network in a real project: where the EN pin actually
# arrives, whether the vendor names it, and which output slots are null. Counts, not examples -
# a rule an adapter relies on has to hold on all of them, not on the one that was dumped.
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\Some.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packagesolt-cli\scripts\probe-nwl-census.py"
#
# The project is COPIED first and the original is never opened. Log next to this file (VOLT_PROBE_LOG
# overrides). ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7 and one non-ASCII byte is a
# SyntaxError before line 1 runs.
import os
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-census.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()





FLAGBITS = ("Negation", "Set", "Jump", "Return", "Rtrig", "Ftrig")

C = {}
EX = {}
def bump(k, ex=None):
    C[k] = C.get(k, 0) + 1
    if ex is not None and k not in EX:
        EX[k] = ex

def names_of(n):
    ip = vp.prop(n, "InputParams")
    if ip is None:
        return None
    try:
        return [str(x) for x in (vp.prop(ip, "Names") or [])]
    except Exception:
        return "<threw>"

def walk(n, where):
    if n is None:
        return
    tn = n.GetType().Name
    fl = vp.prop(n, "Flags")
    if fl is not None:
        for b in FLAGBITS:
            if vp.prop(fl, b):
                bump("itemflag:" + b, where)

    op = vp.prop(n, "Operand")
    if op is not None:
        ofl = vp.prop(op, "Flags")
        if ofl is not None:
            for b in FLAGBITS:
                if vp.prop(ofl, b):
                    bump("operandflag:" + b, where)
        walk(op, where)

    if tn.startswith("BoxTreeBox"):
        en = vp.prop(n, "En")
        ent = "null" if en is None else en.GetType().Name
        bump("En.type=" + ent, where)
        if ent == "Boolean":
            bump("En.bool=" + str(bool(en)), where)
        nm = names_of(n)
        items = []
        try:
            items = list(vp.prop(n, "InputItemList") or [])
        except Exception:
            pass
        cnt = len(items)
        has_en_name = bool(nm) and len(nm) > 0 and nm[0] == "EN"
        if ent == "Boolean" and bool(en):
            bump("EnTrue: Names[0]==EN -> %s" % has_en_name, where)
            bump("EnTrue: inputs==len(Names) -> %s" % (cnt == len(nm or [])), where)
            bump("EnTrue: inputs-len(Names) = %d" % (cnt - len(nm or [])), where)
        else:
            bump("EnNotTrue: Names[0]==EN -> %s" % has_en_name, where)
            bump("EnNotTrue: inputs==len(Names) -> %s" % (cnt == len(nm or [])), where)
        opp = vp.prop(n, "OutputParams")
        onames = None
        if opp is not None:
            try:
                onames = [str(x) for x in (vp.prop(opp, "Names") or [])]
            except Exception:
                onames = None
        outs = vp.prop(n, "Outputs")
        lst = vp.prop(outs, "List") if outs is not None else None
        if lst is not None:
            n_null = sum(1 for x in lst if x is None)
            n_empty = sum(1 for x in lst if x is not None and not (vp.prop(x, "OperandExpr") or ""))
            n_real = len(lst) - n_null - n_empty
            bump("OUT slots=%d null=%d empty=%d REAL=%d" % (len(lst), n_null, n_empty, n_real), where)
            if onames is not None:
                bump("OUT names==slots -> %s" % (len(onames) == len(lst)), where)
                bump("OUT names[0]==ENO -> %s (EnTrue=%s)"
                     % (len(onames) > 0 and onames[0] == "ENO", ent == "Boolean" and bool(en)), where)
                for i, x in enumerate(lst):
                    if x is not None and (vp.prop(x, "OperandExpr") or ""):
                        nmv = onames[i] if i < len(onames) else "<past end>"
                        bump("OUT real at slot %d named %r" % (i, nmv), where)
        for x in items:
            walk(x, where)

    for single in ("RValue", "Input", "Merger"):
        c = vp.prop(n, single)
        if c is not None:
            walk(c, where)
    outs = vp.prop(n, "Outputs")
    if outs is not None:
        lst = vp.prop(outs, "List")
        if lst is not None:
            for x in lst:
                if x is None:
                    bump("assign/box null output entry", where)
                else:
                    ofl = vp.prop(x, "Flags")
                    if ofl is not None:
                        for b in FLAGBITS:
                            if vp.prop(ofl, b):
                                bump("outputflag:" + b, where)
    tr = vp.prop(n, "Trees")
    if tr is not None:
        try:
            for x in list(tr):
                walk(x, where)
        except Exception:
            pass

try:
    import clr, System, shutil
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
    dst = os.path.join(tempfile.gettempdir(), "volt-nwl-census.project")
    if os.path.exists(dst): os.remove(dst)
    shutil.copyfile(SRC, dst)
    log("census of: " + os.path.basename(SRC))
    proj = projects.open(dst)
    pous = [0]
    nets = [0]
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
                        pous[0] += 1
                        for i in range(len(nl)):
                            net = nl[i]; nets[0] += 1
                            cnt = int(vp.prop(net, "NetworkItemCount") or 0)
                            for j in range(cnt):
                                ok, tree = vp.call(net, "GetTree", [j])
                                if ok and tree is not None:
                                    walk(tree, "%s net%d" % (nm, i))
                except Exception:
                    pass
            visit(k, depth + 1)
    visit(proj, 0)
    log("POUs with networks: %d   networks: %d" % (pous[0], nets[0]))
    log("")
    for k in sorted(C):
        log("%-52s %6d   e.g. %s" % (k, C[k], EX.get(k, "")))
    proj.close()
except SystemExit:
    pass
except Exception:
    log(traceback.format_exc())
finally:
    f.close()
    try:
        import System; System.Environment.Exit(0)
    except Exception: pass
