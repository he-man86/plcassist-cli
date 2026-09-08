# IS `VAR / END_VAR` STORED CONTENT, OR DOES THE SCRIPTING API SYNTHESIZE IT?
#
# Volt used to DROP a bare empty VAR block from a property accessor's declaration, on the assumption that it was
# "an empty VAR block the engineer did not author". If the API SYNTHESIZES that text for an accessor that has no
# declaration, dropping it is right and writing it into the workspace file fabricates content. If the project
# STORES it, dropping it loses content.
#
# The distinguishing evidence is the DISTRIBUTION. A synthesized default is a constant: every accessor without a
# real declaration answers with the same string. Stored content varies - some accessors answer "", some answer
# the empty block, some answer a modifier or real variables. So census every accessor in the project and report
# the distinct values with counts.
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\A COPY.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-accessor-census.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII.
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "accessor-census.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def decl_of(node):
    try:
        d = getattr(node, "textual_declaration", None)
        if d is None:
            return "<no textual_declaration attr>"
        t = getattr(d, "text", None)
        return t if t is not None else "<no .text>"
    except Exception as e:
        return "<raised %s>" % e

try:
    proj = projects.open(SRC)

    def walk(n):
        try:
            kids = list(n.get_children())
        except Exception:
            return
        for k in kids:
            yield k
            for x in walk(k):
                yield x

    counts = {}
    examples = {}
    total = 0
    for node in walk(proj):
        # A property's accessors are its children and are named Get / Set.
        try:
            name = str(node.get_name())
        except Exception:
            continue
        if name not in ("Get", "Set"):
            continue
        d = decl_of(node)
        total += 1
        counts[d] = counts.get(d, 0) + 1
        if d not in examples:
            try:
                examples[d] = str(node.get_parent().get_name())
            except Exception:
                examples[d] = "?"

    log("accessors found: %d" % total)
    log("distinct declaration values: %d" % len(counts))
    log("")
    log("=== the distribution (a SYNTHESIZED default would be ONE value for all of them) ===")
    for d in sorted(counts, key=lambda k: -counts[k]):
        log("")
        log("  count %-5d  first seen on property %s" % (counts[d], examples[d]))
        log("  repr: %r" % (d if len(d) < 300 else d[:300] + "...<truncated>"))
    log("")
    log("done")
except Exception:
    log(traceback.format_exc())
finally:
    f.close()
    try:
        import System; System.Environment.Exit(0)
    except Exception:
        pass
