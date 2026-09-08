# DOES A TASK CALL ENTRY CARRY CONTENT VOLT DOES NOT WRITE BACK?
#
# `WriteCallList` rebuilds a task's call list from scratch - clear, then `CreatePouObject(name)` per call - and
# its own doc comment says why: "an entry carries a per-entry COMMENT the descriptor does not, so a positional
# diff would have to preserve something Volt cannot see." That is a correct description of the mechanism and an
# incomplete description of the CONSEQUENCE: every `volt push` that changes a task's call list DELETES those
# comments, and the `.task` file the engineer reads never showed them in the first place, so nothing in the
# workspace or in git can reveal the loss.
#
# Whether that is active data loss or a latent hole is not something to reason about, so this measures it.
#
# TWO SURFACES, and only one of them is the truth:
#   * the SCRIPTING list (`ScriptPouObjectList`) iterates plain NAME STRINGS. A census through it sees no
#     comment field and would have concluded, wrongly, that there is nothing to lose.
#   * one non-public property down is `_3S.CoDeSys.TaskObject.PouObjectList`, holding real
#     `_3S.CoDeSys.TaskObject.PouObject` entries. It must be read by REFLECTION - IronPython answers "no
#     attribute 'PouObjectList'" for a property that object's own reflection listing shows.
#
# The vendor states the entry's whole persisted contract itself: `PouObject.SerializableValueNames` is exactly
# ('Name', 'Comment'). So there are two fields, Volt carries one, and the only open question is the
# DISTRIBUTION - a constant means the API synthesizes it, variety means the project stores it.
#
#   pwsh> $env:VOLT_PROBE_PROJECTS="C:\...\a.project;C:\...\b.project"
#         Start-Process CODESYS.exe -ArgumentList '--profile="..."','--noUI','--runscript="...\probe-task-callcomment.py"' -Wait
#
# ASCII ONLY - CODESYS compiles this as ASCII IronPython 2.7.
import os
import shutil
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "task-callcomment.log")
SRCS = [s for s in (os.environ.get("VOLT_PROBE_PROJECTS") or "").split(";") if s.strip()]

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

def prop(o, name):
    if o is None:
        return None
    try:
        p = o.GetType().GetProperty(name, _bf())
        return p.GetValue(o, None) if p is not None else None
    except Exception:
        return None

def entries_of(scripting_list):
    """The real entry objects behind the scripting wrapper, or [] if the shape is not what was measured."""
    raw = prop(scripting_list, "PouObjectList")
    if raw is None:
        return None
    try:
        return list(raw)
    except Exception:
        return None

try:
    import System
    if not SRCS:
        log("VOLT_PROBE_PROJECTS is empty"); raise SystemExit

    tasks = 0
    entries = 0
    unreachable = 0
    contract = {}          # repr(SerializableValueNames) -> count
    comments = {}          # repr(Comment) -> count
    where = {}             # repr(Comment) -> first place it was seen

    for src in SRCS:
        src = src.strip()
        label = os.path.basename(src)
        if not os.path.exists(src):
            log("!! missing: %s" % src)
            continue

        # Never open the engineer's own file: a scripting open can dirty a project.
        dst = os.path.join(tempfile.gettempdir(), "volt-taskcall.project")
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copyfile(src, dst)
        proj = projects.open(dst)

        per_task = [0]
        per_entry = [0]
        per_named = [0]

        def visit(node, depth):
            global tasks, entries, unreachable
            if depth > 14:
                return
            try:
                kids = list(node.get_children())
            except Exception:
                return
            for k in kids:
                pous = None
                for cand in ("PouCalls", "pous", "Pous"):
                    try:
                        pous = getattr(k, cand, None)
                    except Exception:
                        pous = None
                    if pous is not None:
                        break
                if pous is not None:
                    items = entries_of(pous)
                    if items is None:
                        # The shape is not what was measured. Say so loudly rather than counting zero, which
                        # would read as "no comments found".
                        try:
                            n = len(list(pous))
                        except Exception:
                            n = 0
                        if n:
                            unreachable += n
                    elif items:
                        tasks += 1
                        per_task[0] += 1
                        for e in items:
                            entries += 1
                            per_entry[0] += 1
                            c = repr(prop(e, "Comment"))
                            comments[c] = comments.get(c, 0) + 1
                            if c not in where:
                                try:
                                    where[c] = "%s / %s / %s" % (label, str(k.get_name()), prop(e, "Name"))
                                except Exception:
                                    where[c] = label
                            if c not in ("''", "None"):
                                per_named[0] += 1
                            sv = repr(prop(e, "SerializableValueNames"))
                            contract[sv] = contract.get(sv, 0) + 1
                visit(k, depth + 1)

        visit(proj, 0)
        log("== %-42s tasks: %-3d entries: %-3d with a comment: %d"
            % (label, per_task[0], per_entry[0], per_named[0]))
        proj.close()

    log("")
    log("=== HOW FAR THE WALK GOT (nothing below is evidence if these are zero) ===")
    log("  tasks with a non-empty call list: %d" % tasks)
    log("  call entries examined:            %d" % entries)
    if unreachable:
        log("  !! entries the raw list could NOT be read for: %d - the shape changed, fix the probe" % unreachable)
    log("")
    log("=== the vendor's own statement of what an entry PERSISTS ===")
    for k in sorted(contract, key=lambda x: -contract[x]):
        log("  %-60s x%d" % (k[:60], contract[k]))
    log("")
    log("=== Comment: the distribution ===")
    log("(a CONSTANT means the API synthesizes it; VARIETY means the project stores it)")
    for k in sorted(comments, key=lambda x: -comments[x]):
        log("  x%-5d %-50s [%s]" % (comments[k], k[:50], where.get(k, "?")))
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
