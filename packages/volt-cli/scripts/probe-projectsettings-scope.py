# DOES THE COMPILER CONFIGURATION FOLLOW THE LOADED PROJECT, OR IS IT THE SESSION'S?
#
# `ProjectSettingsDescriptor` reads `APEnvironment.LMServiceProvider -> ConfigurationService ->
# WarningConfiguration / CompileOptions`. That provider is a SINGLETON on the engine, not a property of the
# node being described, so the descriptor for project A could be reporting whatever project B last put there.
#
# `project-settings-sync` opens on that doubt and puts the READ first for a reason: making the descriptor
# writable while it can misread would take a value Volt got wrong and write it into the engineer's project,
# and a round-trip test would call that success because both halves agree with each other.
#
# THE EXPERIMENT IS A SWITCH, not a single read. Open A, read; close; open B, read; close; open A again, read.
# The corpus supplies a pair that disagrees in two independent fields, which is what makes a stale answer
# unmistakable rather than a judgement call:
#
#     Pro2193-94-95-96_COdesys   Disabled warnings: C0371    UTF-8 encoding: off
#     CodesysTestProject         Disabled warnings: (none)   UTF-8 encoding: ON
#
# So:
#   * B reporting C0371, or A reporting UTF-8 on   -> the singleton is STALE and the read is untrustworthy.
#   * each project reporting its own values        -> the provider follows the load, and the descriptor is
#                                                     sound in a session that opens one project at a time.
#   * the FIRST read (before any project) answering with values at all is itself a finding: it would mean the
#     service has a state that is nobody's project.
#
#   pwsh> $env:VOLT_PROBE_A="...\Pro2193-94-95-96_COdesys.project"
#         $env:VOLT_PROBE_B="...\CodesysTestProject.project"
#         Start-Process CODESYS.exe -ArgumentList '--profile="..."','--noUI','--runscript="...\probe-projectsettings-scope.py"' -Wait
#
# ASCII ONLY - CODESYS compiles this as IronPython 2.7.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voltprobe as vp

log, done = vp.logger("projectsettings-scope.log")

A = os.environ.get("VOLT_PROBE_A") or ""
B = os.environ.get("VOLT_PROBE_B") or ""


def read_config():
    """The PRODUCTION read, reproduced exactly - same static, same members, same getters as
    `CodesysObjectModel.ProjectSettingsDescriptor`. A probe that reached the values a different way would
    prove something about a path Volt does not take."""
    import System
    provider = None
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        try:
            t = asm.GetType("_3S.CoDeSys.Engine.APEnvironment")
        except Exception:
            continue
        if t is None:
            continue
        p = t.GetProperty("LMServiceProvider")
        if p is None:
            continue
        provider = p.GetValue(None, None)
        if provider is not None:
            break
    if provider is None:
        return {"!": "APEnvironment.LMServiceProvider unavailable"}

    config = vp.prop(provider, "ConfigurationService")
    if config is None:
        return {"!": "ConfigurationService unavailable"}

    warnings = vp.prop(config, "WarningConfiguration")
    options = vp.prop(config, "CompileOptions")

    def ids(getter):
        ok, res = vp.call(warnings, getter, []) if warnings is not None else (False, "no WarningConfiguration")
        if not ok:
            return "<%s>" % res
        if res is None:
            return "(null)"
        try:
            out = sorted("C%04d" % int(str(x)) for x in res if x is not None)
        except Exception:
            return "<unreadable>"
        return ", ".join(out) if out else "(empty)"

    def flag(name):
        v = vp.prop(options, name) if options is not None else None
        return "on" if v is True else ("off" if v is False else repr(v))

    return {
        "Disabled warnings": ids("GetDisabledWarningIds"),
        "Warnings as errors": ids("GetWarningAsErrorIds"),
        "Replace constants": flag("ReplaceConstants"),
        "UTF-8 encoding": flag("UTF8Encoding"),
        "Max compiler warnings": repr(vp.prop(options, "MaxCompilerWarnings") if options is not None else None),
        "service id": "%s#%s" % (config.GetType().Name, id(config)) if config is not None else "-",
    }


def report(stage):
    log("== %s" % stage)
    cfg = read_config()
    for k in sorted(cfg):
        log("     %-24s %s" % (k, cfg[k]))
    log("")
    return cfg


try:
    if not A or not B:
        log("VOLT_PROBE_A and VOLT_PROBE_B must both be set")
        done()

    log("A = %s" % os.path.basename(A))
    log("B = %s" % os.path.basename(B))
    log("")

    # Before anything is loaded. Values here belong to no project at all.
    before = report("0. no project open")

    proj = vp.open_copy(projects, A, "psA")
    a1 = report("1. A open")
    proj.close()

    afterclose = report("2. A closed, nothing open")

    proj = vp.open_copy(projects, B, "psB")
    b1 = report("3. B open (A was open before it)")
    proj.close()

    proj = vp.open_copy(projects, A, "psA2")
    a2 = report("4. A open again (B was open before it)")
    proj.close()

    log("=== THE VERDICT ===")
    fields = ["Disabled warnings", "UTF-8 encoding"]
    stale = False
    for f in fields:
        log("  %-22s  A=%-14s B=%-14s A again=%s" % (f, a1.get(f), b1.get(f), a2.get(f)))
        if a1.get(f) == b1.get(f):
            stale = True
    log("")
    if stale:
        log("STALE: A and B report the SAME value for a field the two projects disagree on, so the")
        log("configuration service does NOT follow the loaded project. The descriptor cannot be trusted in a")
        log("session that has opened more than one project, and must not be made writable as it stands.")
    else:
        log("PER-PROJECT: each project reported its own values, so the provider follows the load. The")
        log("singleton is a singleton SERVICE over per-project state, not shared state.")
    log("")
    log("(service id across stages: %s / %s / %s / %s / %s)"
        % (before.get("service id"), a1.get("service id"), afterclose.get("service id"),
           b1.get("service id"), a2.get("service id")))
    log("")
    log("done")
    done()
except Exception:
    done(error=True)
