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
#     attribute 'PouObjectList'" for a property that object's own reflection listing shows. `voltprobe.prop`
#     does that, which is most of why it exists.
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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp

log, done = vp.logger("task-callcomment.log")
SRCS = vp.projects_from_env()


def entries_of(scripting_list):
    """The real entry objects behind the scripting wrapper, or None if the shape is not what was measured."""
    raw = vp.prop(scripting_list, "PouObjectList")
    if raw is None:
        return None
    try:
        return list(raw)
    except Exception:
        return None


def call_list_of(node):
    """A task node's call list, under whichever name this build exposes."""
    for cand in ("PouCalls", "pous", "Pous"):
        try:
            v = getattr(node, cand, None)
        except Exception:
            v = None
        if v is not None:
            return v
    return None


try:
    if not SRCS:
        log("VOLT_PROBE_PROJECTS is empty")
        done()

    tasks = 0
    entries = 0
    unreachable = 0
    contract = {}          # repr(SerializableValueNames) -> count
    comments = {}          # repr(Comment) -> count
    where = {}             # repr(Comment) -> first place it was seen

    for src in SRCS:
        if not os.path.exists(src):
            log("!! missing: %s" % src)
            continue
        label = os.path.basename(src)
        proj = vp.open_copy(projects, src, "taskcall")

        per_task = 0
        per_entry = 0
        per_named = 0

        for node in vp.walk(proj):
            pous = call_list_of(node)
            if pous is None:
                continue
            items = entries_of(pous)
            if items is None:
                # The shape is not what was measured. Say so LOUDLY rather than counting zero, which would
                # read as "no comments found".
                try:
                    n = len(list(pous))
                except Exception:
                    n = 0
                unreachable += n
                continue
            if not items:
                continue

            tasks += 1
            per_task += 1
            for e in items:
                entries += 1
                per_entry += 1
                c = repr(vp.prop(e, "Comment"))
                comments[c] = comments.get(c, 0) + 1
                if c not in where:
                    try:
                        where[c] = "%s / %s / %s" % (label, str(node.get_name()), vp.prop(e, "Name"))
                    except Exception:
                        where[c] = label
                if c not in ("''", "None"):
                    per_named += 1
                sv = repr(vp.prop(e, "SerializableValueNames"))
                contract[sv] = contract.get(sv, 0) + 1

        log("== %-42s tasks: %-3d entries: %-3d with a comment: %d" % (label, per_task, per_entry, per_named))
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
    done()
except Exception:
    done(error=True)
