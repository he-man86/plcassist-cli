# -*- coding: utf-8 -*-
"""
Open a fixture project, then start Volt THE WAY A USER DOES.

`run_pipe_headless.py` is the CI/dev loop: it opens the project, loads the bridge DLL from the build output and
PUMPS the message loop itself, because headless CODESYS has none running. That pump is a test-harness thing, and
it means the e2e never exercised the path an engineer actually takes.

This runs the SHIPPED script instead — `start_volt_codesys.py`, verbatim, via execfile — inside a normal GUI
CODESYS. The difference is not cosmetic:

  - it loads the bridge from a PER-SESSION TEMP COPY (so an install can update while the IDE is open), where the
    headless script loads the build output directly;
  - `PipeHost.Start` returns immediately and the IDE'S OWN message loop serves the pipe, where the headless
    script owns the loop.

The only thing scripted here that a user does by hand is OPENING the project — everything after that is the
production script, unmodified. Stop it the way a user does too: run `stop_volt_codesys.py` from the IDE.

Driven by `codesys-pipe.ps1 up -Production` (which implies -Ui).
"""
from __future__ import print_function
import os

_FIXTURE = os.environ.get("VOLT_FIXTURE_PROJECT")
_HERE = os.path.dirname(os.path.abspath(__file__))


def _open_fixture():
    """Open the fixture, or keep whatever is already open. A user opens their project before starting Volt; this
    is that step and nothing more."""
    if not _FIXTURE:
        print("[volt-pipe-production] no VOLT_FIXTURE_PROJECT - using whatever project is open")
        return
    try:
        if projects.primary is not None:
            print("[volt-pipe-production] a project is already open - leaving it")
            return
    except Exception:
        pass
    print("[volt-pipe-production] opening fixture: %s" % _FIXTURE)
    projects.open(_FIXTURE)
    print("[volt-pipe-production] fixture opened")


_open_fixture()

# The SHIPPED script, run as-is. Not imported and not copied: any drift between what is tested and what users run
# is the whole thing this file exists to prevent.
#
# NOT `execfile`. SP21's scripting engine is PYTHON 3, where that builtin no longer exists - and the failure is
# not a clean one: the DeprecationWarning it raises lands in CODESYS's message store, which `build` reads, so
# every e2e test that compiles reported two phantom build ERRORS. `compile`+`exec` is what both 2.x and 3.x have.
# (Several comments in the shipped scripts still say "IronPython 2.7"; that is true of SP18, not of SP21.)
_start = os.path.join(_HERE, "start_volt_codesys.py")
print("[volt-pipe-production] running the production script: %s" % _start)
with open(_start) as _f:
    _src = _f.read()
exec(compile(_src, _start, "exec"))
print("[volt-pipe-production] production script returned - the IDE's own loop now serves the pipe")
