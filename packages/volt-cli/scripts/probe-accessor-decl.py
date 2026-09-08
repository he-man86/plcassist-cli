# WHAT DOES CODESYS ACTUALLY HOLD FOR A PROPERTY'S GET AND SET DECLARATION?
#
# `AccessorDeclaration.Keep` DROPS an accessor declaration that is a bare `VAR`/`END_VAR`, on the stated grounds
# that it "carries nothing" and that keeping it would write an empty VAR block the engineer never authored. That
# rule is invisible to every round-trip test Volt has: the corpus is itself a pull, so if the read drops content
# the corpus and any migrated copy are wrong in the SAME way and compare equal.
#
# So ask the IDE directly. For one property with a visibly asymmetric pair - pro2193's
# `CassetteFB.NegativeLimitReachedY`, whose GET materializes with NO declaration while its SET keeps
# `PRIVATE / VAR / END_VAR` - dump what the vendor reports for each accessor, verbatim and with repr().
#
#   pwsh> $env:VOLT_PROBE_PROJECT="...\Pro2193-94-95-96_COdesys.project"
#         & "C:\Program Files\CODESYS 3.5.21.40\CODESYS\Common\CODESYS.exe" `
#           --profile="CODESYS V3.5 SP21 Patch 4" --noUI --runscript="<repo>\packages\volt-cli\scripts\probe-accessor-decl.py"
#
# ASCII ONLY - CODESYS compiles this as ASCII.
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("VOLT_PROBE_LOG") or os.path.join(HERE, "accessor-decl.log")
SRC = os.environ.get("VOLT_PROBE_PROJECT") or ""
WANT_POU = os.environ.get("VOLT_PROBE_POU") or "CassetteFB"
WANT_PROP = os.environ.get("VOLT_PROBE_PROP") or "NegativeLimitReachedY"

f = open(LOG, "w")
def log(s):
    f.write(str(s) + "\n"); f.flush()

def decl_of(node):
    """The declaration text the IDE holds for a node, or a marker saying why there is none."""
    for attr in ("textual_declaration", "declaration"):
        try:
            d = getattr(node, attr, None)
            if d is None:
                continue
            txt = getattr(d, "text", None)
            return txt if txt is not None else str(d)
        except Exception as e:
            return "<%s raised %s>" % (attr, e)
    return "<no textual_declaration>"

try:
    if not SRC or not os.path.exists(SRC):
        log("set VOLT_PROBE_PROJECT to a copy of the project")
    else:
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

        pou = None
        for node in walk(proj):
            try:
                if str(node.get_name()) == WANT_POU:
                    pou = node
                    break
            except Exception:
                continue
        if pou is None:
            log("POU %s not found" % WANT_POU)
        else:
            log("POU %s found: %s" % (WANT_POU, pou.GetType().Name))
            prop = None
            for k in walk(pou):
                try:
                    if str(k.get_name()) == WANT_PROP:
                        prop = k
                        break
                except Exception:
                    continue
            if prop is None:
                log("property %s not found under %s" % (WANT_PROP, WANT_POU))
            else:
                log("")
                log("=== PROPERTY %s ===" % WANT_PROP)
                log("  declaration: %r" % decl_of(prop))
                for acc in prop.get_children():
                    name = str(acc.get_name())
                    log("")
                    log("  --- accessor %s (%s) ---" % (name, acc.GetType().Name))
                    log("      declaration repr: %r" % decl_of(acc))
                    try:
                        impl = acc.textual_implementation.text
                    except Exception as e:
                        impl = "<%s>" % e
                    log("      implementation  : %r" % impl)
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
