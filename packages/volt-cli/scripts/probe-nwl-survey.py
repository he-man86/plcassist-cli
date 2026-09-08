# Survey a REAL project's graphical bodies through the 3S NWL object model, and report what an
# adapter must actually handle: item types, flags, split points, LD structures, network metadata.
#
#   pwsh> & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI `
#           --runscript="<repo>\packages\volt-cli\scripts\probe-nwl-survey.py"
#
# VOLT_SURVEY_PROJECT names the .project; it is COPIED first and the original is never opened.
# Log next to this file (VOLT_PROBE_LOG overrides). ASCII ONLY - CODESYS compiles this as ASCII
# IronPython 2.7 and one non-ASCII byte is a SyntaxError before line 1 runs.
import os
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-survey.log")
SRC = os.environ.get("VOLT_SURVEY_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()





FLAGBITS = ("Negation", "Set", "Jump", "Return", "Rtrig", "Ftrig")

class Stats(object):
    def __init__(self):
        self.items = {}
        self.flags = {}
        self.boxtypes = {}
        self.pous = 0
        self.networks = 0
        self.trees = 0
        self.null_trees = 0
        self.splits = 0
        self.split_examples = []
        self.titled = 0
        self.labelled = 0
        self.commented = 0
        self.disabled = 0
        self.multi_output = 0
        self.eneno = 0
        self.stsnippet = 0
        self.maxdepth = 0
        self.examples = {}

    def bump(self, d, k):
        d[k] = d.get(k, 0) + 1

S = Stats()

def walk_item(n, depth, where):
    if n is None:
        return
    S.maxdepth = max(S.maxdepth, depth)
    tn = n.GetType().Name
    S.bump(S.items, tn)
    if tn not in S.examples:
        S.examples[tn] = where

    fl = vp.prop(n, "Flags")
    if fl is not None:
        for b in FLAGBITS:
            if vp.prop(fl, b):
                S.bump(S.flags, b)

    bt = vp.prop(n, "BoxType")
    if bt:
        S.bump(S.boxtypes, str(bt))
    if vp.prop(n, "EnEno"):
        S.eneno += 1
    if vp.prop(n, "ProvidesSTSnippet"):
        S.stsnippet += 1

    op = vp.prop(n, "Operand")
    if op is not None:
        walk_item(op, depth + 1, where)
    rv = vp.prop(n, "RValue")
    if rv is not None:
        walk_item(rv, depth + 1, where)

    outs = vp.prop(n, "Outputs")
    if outs is not None:
        lst = vp.prop(outs, "List")
        if lst is not None:
            if len(lst) > 1:
                S.multi_output += 1
            for x in lst:
                walk_item(x, depth + 1, where)

    for coll in ("InputItemList", "Trees"):
        c = vp.prop(n, coll)
        if c is not None:
            try:
                for x in c:
                    walk_item(x, depth + 1, where)
            except Exception:
                pass
    for single in ("Input", "Merger"):
        c = vp.prop(n, single)
        if c is not None:
            walk_item(c, depth + 1, where)

try:
    import clr
    import System
    import shutil

    if not SRC or not os.path.exists(SRC):
        log("VOLT_SURVEY_PROJECT not set or missing: %r" % SRC)
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

    dst = os.path.join(tempfile.gettempdir(), "volt-nwl-survey.project")
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copyfile(SRC, dst)
    log("survey of: " + os.path.basename(SRC))
    proj = projects.open(dst)                                    # noqa: F821
    log("opened (a copy; the original is never touched)")

    aspects = {}

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
            u = vp.unwrap(k)
            g = vp.prop(u, "guid")
            if g is not None:
                try:
                    meta = objmgr.GetObjectToRead(vp.prop(u, "handle") or 0, g)
                    iobj = vp.prop(meta, "Object")
                    if iobj is not None and "POUObject" in iobj.GetType().FullName:
                        impl = vp.prop(iobj, "Implementation")
                        if impl is not None:
                            an = impl.GetType().Name
                            aspects[an] = aspects.get(an, 0) + 1
                            nets = vp.prop(impl, "NetworkList")
                            if nets is not None:
                                if not hasattr(S, "_dumped"):
                                    S._dumped = True
                                    log("")
                                    log("### the implementation aspect's own properties (%s) ###" % nm)
                                    for pp in sorted(impl.GetType().GetProperties(vp.bf()), key=lambda x: x.Name):
                                        try:
                                            v = pp.GetValue(impl, None)
                                        except Exception:
                                            v = "<threw>"
                                        if pp.Name in ("NetworkList",):
                                            v = "<%d networks>" % len(v)
                                        log("    %-34s = %r" % (pp.Name, v))
                                S.pous += 1
                                survey_networks(nets, nm)
                except Exception:
                    pass
            visit(k, depth + 1)

    def survey_networks(nets, pouname):
        for i in range(len(nets)):
            net = nets[i]
            S.networks += 1
            if vp.prop(net, "Title"):
                S.titled += 1
            if vp.prop(net, "Label"):
                S.labelled += 1
            if vp.prop(net, "Comment"):
                S.commented += 1
            if vp.prop(net, "OutCommented"):
                S.disabled += 1
            cnt = vp.prop(net, "NetworkItemCount") or 0
            for j in range(int(cnt)):
                ok, tree = vp.call(net, "GetTree", [j])
                if not ok or tree is None:
                    S.null_trees += 1
                    continue
                S.trees += 1
                walk_item(tree, 0, "%s net%d" % (pouname, i))
            for j in range(0, 64):
                ok, sp = vp.call(net, "GetSplitPoint", [j])
                if not ok or sp is None:
                    break
                S.splits += 1
                if len(S.split_examples) < 8:
                    S.split_examples.append("%s net%d split[%d] = %r"
                                            % (pouname, i, j, vp.prop(sp, "OperandExpr")))

    visit(proj, 0)

    # A full structural dump of a few REAL ladder networks, so Demux/Parallel/Terminator can be
    # read in context rather than inferred from a count.
    WANT = os.environ.get("VOLT_SURVEY_POU") or "Mach1_Drives"
    def show(n, indent):
        if n is None:
            return
        pad = " " * indent
        bits = []
        for pn in ("OperandExpr", "BoxType", "VarId", "Mode", "CallType", "EnEno", "IsLValue"):
            v = vp.prop(n, pn)
            if v is not None and v != "" and v is not False:
                bits.append("%s=%s" % (pn, v))
        fl = vp.prop(n, "Flags")
        if fl is not None:
            on = [x for x in FLAGBITS if vp.prop(fl, x)]
            if on:
                bits.append("Flags=" + ",".join(on))
        log("%s%s %s" % (pad, n.GetType().Name, " ".join(bits)))
        for sub in ("Operand", "RValue", "Input", "Merger"):
            v = vp.prop(n, sub)
            if v is not None:
                log("%s  .%s" % (pad, sub))
                show(v, indent + 4)
        outs = vp.prop(n, "Outputs")
        if outs is not None:
            lst = vp.prop(outs, "List")
            if lst is not None and len(lst) > 0:
                log("%s  .Outputs (%d)" % (pad, len(lst)))
                for x in lst:
                    show(x, indent + 4)
        for coll in ("InputItemList", "Trees"):
            c = vp.prop(n, coll)
            if c is not None:
                try:
                    k = len(c)
                except Exception:
                    k = 0
                if k:
                    log("%s  .%s (%d)" % (pad, coll, k))
                    for x in c:
                        show(x, indent + 4)

    def dump_pou(node, depth):
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
            if nm == WANT:
                u = vp.unwrap(k)
                meta = objmgr.GetObjectToRead(vp.prop(u, "handle") or 0, vp.prop(u, "guid"))
                impl = vp.prop(vp.prop(meta, "Object"), "Implementation")
                nets = vp.prop(impl, "NetworkList")
                if nets is None:
                    continue
                log("")
                log("############ FULL DUMP: %s (%d networks) ############" % (nm, len(nets)))
                for i in range(min(4, len(nets))):
                    net = nets[i]
                    log("")
                    log("--- network[%d] Title=%r Comment=%r OutCommented=%s items=%s ---"
                        % (i, vp.prop(net, "Title"), vp.prop(net, "Comment"),
                           vp.prop(net, "OutCommented"), vp.prop(net, "NetworkItemCount")))
                    for j in range(int(vp.prop(net, "NetworkItemCount") or 0)):
                        ok, tree = vp.call(net, "GetTree", [j])
                        if ok and tree is not None:
                            show(tree, 2)
                return
            dump_pou(k, depth + 1)

    dump_pou(proj, 0)

    log("")
    log("=== implementation aspects across the project ===")
    for k in sorted(aspects, key=lambda x: -aspects[x]):
        log("  %-34s %d" % (k, aspects[k]))

    log("")
    log("=== graphical bodies ===")
    log("  POUs with NetworkList : %d" % S.pous)
    log("  networks              : %d" % S.networks)
    log("  trees                 : %d" % S.trees)
    log("  NULL trees (skipped)  : %d" % S.null_trees)
    log("  max tree depth        : %d" % S.maxdepth)

    log("")
    log("=== SPLIT POINTS (the blocking unknown) ===")
    log("  total: %d" % S.splits)
    for e in S.split_examples:
        log("    " + e)

    log("")
    log("=== item types actually used ===")
    for k in sorted(S.items, key=lambda x: -S.items[x]):
        log("  %-24s %6d   e.g. %s" % (k, S.items[k], S.examples.get(k, "")))

    log("")
    log("=== IFlags bits actually used ===")
    if not S.flags:
        log("  (none)")
    for k in sorted(S.flags, key=lambda x: -S.flags[x]):
        log("  %-12s %d" % (k, S.flags[k]))

    log("")
    log("=== network metadata ===")
    log("  with Title       : %d" % S.titled)
    log("  with Label       : %d" % S.labelled)
    log("  with Comment     : %d" % S.commented)
    log("  OutCommented     : %d" % S.disabled)
    log("  multi-output assigns : %d" % S.multi_output)
    log("  EnEno boxes          : %d" % S.eneno)
    log("  ST-snippet boxes     : %d" % S.stsnippet)

    log("")
    log("=== box types (top 40) ===")
    for k in sorted(S.boxtypes, key=lambda x: -S.boxtypes[x])[:40]:
        log("  %-28s %d" % (k, S.boxtypes[k]))

    proj.close()
    log("")
    log("=== done ===")
except Exception:
    log(traceback.format_exc())
f.close()
try:
    system.exit()                                                # noqa: F821
except Exception:
    pass
