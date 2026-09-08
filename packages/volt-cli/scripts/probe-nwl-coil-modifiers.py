# DOES A COIL EVER CARRY A MODIFIER VOLT CANNOT WRITE?
#
# `NetworkTextWriter.AssignOp` renders an assignment TARGET's flags as `:=` / `S=` / `R=`, reading only Set and
# Reset. `CodesysNetworkReader.ReadTarget` keeps Rising/Falling on that same target - they come through
# ReadFlags and the coil decode overwrites only Negated/Set/Reset. So a rising-edge coil READS as one and
# WRITES as a plain coil: the pulled text says `out := a;`, which is a different machine.
#
# The vendor reference confirms the element exists - `<coil edge="rising">` / `<coil edge="falling">`, inserted
# with the Edge Detection command on a coil output (15-ld-elements.md). What is NOT known is whether real
# projects contain one, and that is the whole question, because the fixed-point round trip is blind to it: a
# flag lost on the PULL is absent from both sides of the comparison and re-emits identically forever.
#
# So census every assignment target in every project and report the flag combos, with the vendor's own PLCopen
# word for any combo that is not one of the three already measured (none / Set / Negation+Set).
#
#   pwsh> $env:VOLT_PROBE_PROJECTS="C:\...\a.project;C:\...\b.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-nwl-coil-modifiers.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import re
import shutil
import tempfile
import traceback
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp


HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "nwl-coil-modifiers.log")
SRCS = [s for s in (os.environ.get("VOLT_PROBE_PROJECTS") or "").split(";") if s.strip()]

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()





# The bits ReadFlags reads, in its order. Rtrig/Ftrig are the two AssignOp cannot render.
FLAGBITS = ("Negation", "Set", "Jump", "Return", "Rtrig", "Ftrig")
# The three combos already measured on a target (NetworkModel.Flags.CoilFromVendor). Anything else is news.
KNOWN = ("none", "Set", "Negation+Set")

def combo(fl):
    if fl is None:
        return "none"
    on = [b for b in FLAGBITS if vp.prop(fl, b)]
    return "+".join(on) if on else "none"

def operand_text(o):
    for name in ("OperandExpr", "Operand", "Text", "Name"):
        v = vp.prop(o, name)
        if v is not None:
            s = str(v)
            if s:
                return s[:40]
    return "?"

try:
    import clr, System
    if not SRCS:
        log("VOLT_PROBE_PROJECTS is empty"); raise SystemExit

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
        log("ObjectMgr NOT reachable"); raise SystemExit

    # A probe that reports "found nothing" without saying how far it GOT proves nothing: "this project has no
    # ladder" and "the walk broke on the first node" produce the same empty census. Count every stage.
    stats = {}

    def bump(k, n=1):
        stats[k] = stats.get(k, 0) + n

    seen_types = {}

    grand = {}        # combo -> total count across all projects
    exotic = []       # (project, pou, combo, operand) for anything not in KNOWN
    exotic_objs = {}  # (project, pou) -> scripting object, for the PLCopen correlation

    for src in SRCS:
        src = src.strip()
        label = os.path.basename(src)
        if not os.path.exists(src):
            log("!! missing: %s" % src)
            continue

        # Never open the engineer's own file: a scripting open can dirty a project.
        dst = os.path.join(tempfile.gettempdir(), "volt-coilmod.project")
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copyfile(src, dst)
        proj = projects.open(dst)

        per = {}

        def note(c):
            per[c] = per.get(c, 0) + 1
            grand[c] = grand.get(c, 0) + 1

        def walk(n, pou):
            if n is None:
                return
            try:
                tn = n.GetType().Name
            except Exception:
                return
            seen_types[tn] = seen_types.get(tn, 0) + 1
            bump("tree nodes visited")
            if tn == "BoxTreeAssign":
                bump("BoxTreeAssign")
                outs = vp.prop(n, "Outputs")
                lst = vp.prop(outs, "List") if outs is not None else None
                if lst is not None:
                    for x in lst:
                        if x is None:
                            continue
                        c = combo(vp.prop(x, "Flags"))
                        note(c)
                        if c not in KNOWN:
                            exotic.append((label, pou, c, operand_text(x)))
            for single in ("RValue", "Input", "Merger", "Operand"):
                c = vp.prop(n, single)
                if c is not None:
                    walk(c, pou)
            for coll in ("InputItemList", "Trees"):
                c = vp.prop(n, coll)
                if c is not None:
                    try:
                        for x in c:
                            walk(x, pou)
                    except Exception:
                        pass

        def visit(node, depth):
            if depth > 14:
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
                bump("tree nodes")
                if g is not None:
                    try:
                        meta = objmgr.GetObjectToRead(vp.prop(u, "handle") or 0, g)
                        iobj = vp.prop(meta, "Object")
                        impl = vp.prop(iobj, "Implementation") if iobj is not None else None
                        nl = vp.prop(impl, "NetworkList") if impl is not None else None
                        if nl is not None:
                            bump("POUs with a NetworkList")
                            before = len(exotic)
                            for i in range(len(nl)):
                                net = nl[i]
                                bump("networks")
                                cnt = int(vp.prop(net, "NetworkItemCount") or 0)
                                bump("network items", cnt)
                                for j in range(cnt):
                                    ok, tree = vp.call(net, "GetTree", [j])
                                    if ok and tree is not None:
                                        bump("trees")
                                        walk(tree, nm)
                                    elif not ok:
                                        bump("GetTree FAILED")
                            if len(exotic) > before:
                                exotic_objs[(label, nm)] = k
                    except Exception:
                        pass
                visit(k, depth + 1)

        visit(proj, 0)
        log("== %s" % label)
        for c in sorted(per, key=lambda k: -per[k]):
            log("     %-24s x%-6d%s" % (c, per[c], "" if c in KNOWN else "   <-- NOT PREVIOUSLY MEASURED"))
        log("")

        # The vendor's own word, for POUs that produced something unmeasured.
        for key in sorted(exotic_objs):
            plabel, pou = key
            if plabel != label:
                continue
            obj = exotic_objs[key]
            out = os.path.join(tempfile.gettempdir(),
                               "volt-coilmod-%s.xml" % re.sub(r"[^A-Za-z0-9_]", "_", plabel + "-" + pou))
            try:
                if os.path.exists(out):
                    os.remove(out)
                proj.export_xml([obj], out)
                xml = open(out, "rb").read().decode("utf-8", "replace")
                seen = {}
                for m in re.finditer(r"<coil\b[^>]*>", xml):
                    tag = m.group(0)
                    mn = re.search(r'negated="(\w+)"', tag)
                    ms = re.search(r'storage="(\w+)"', tag)
                    me = re.search(r'edge="(\w+)"', tag)
                    k2 = "negated=%s storage=%s edge=%s" % (
                        mn.group(1) if mn else "?", ms.group(1) if ms else "?", me.group(1) if me else "-")
                    seen[k2] = seen.get(k2, 0) + 1
                log("     PLCopen <coil> in %s:" % pou)
                for k2 in sorted(seen):
                    log("        %-46s x%d" % (k2, seen[k2]))
            except Exception:
                log("     PLCopen for %s: export threw %s"
                    % (pou, traceback.format_exc().splitlines()[-1][:70]))
        proj.close()

    log("")
    log("=== HOW FAR THE WALK GOT (an empty census below means nothing only if these are non-zero) ===")
    for k in sorted(stats):
        log("  %-28s %d" % (k, stats[k]))
    log("")
    log("=== node types seen inside the trees (top 25) ===")
    for k in sorted(seen_types, key=lambda x: -seen_types[x])[:25]:
        log("  %-36s x%d" % (k, seen_types[k]))
    log("")
    log("=== ALL PROJECTS: assignment-target flag combos ===")
    total = sum(grand.values()) or 1
    for c in sorted(grand, key=lambda k: -grand[k]):
        log("  %-24s x%-7d %5.2f%%%s"
            % (c, grand[c], 100.0 * grand[c] / total,
               "" if c in KNOWN else "   <-- AssignOp CANNOT RENDER THIS"))
    log("")
    if exotic:
        log("=== every unmeasured target, in full (%d) ===" % len(exotic))
        for p, pou, c, op in exotic:
            log("  %-28s %-28s %-24s %s" % (p[:28], pou[:28], c, op))
    else:
        log("No assignment target outside the three measured combos, in %d project(s)." % len(SRCS))
        log("Rtrig/Ftrig on a coil is REACHABLE per the vendor reference (<coil edge=..>, the Edge Detection")
        log("command) but does not occur here - so the write hole is latent, not active data loss.")
    log("")
    log("done")
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
