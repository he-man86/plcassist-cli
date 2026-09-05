/**
 * `???` — the vendor's marker for a graphical slot nobody named — against the real compiler.
 *
 * WHY THESE EXIST. `???` is not Volt's spelling: CODESYS writes it into a box whose instance is unnamed, or a
 * coil with no target, and draws it so the engineer sees the mistake. Volt carries it through verbatim, and the
 * LSP reports one `NETWORK_UNRESOLVED_BOX` per marker. Nothing had ever checked that claim against the
 * compiler — the conformance recorder's header said graphical bodies "can't be recorded, the bridge stores them
 * as PlcOpen XML, not pushable text", which stopped being true when network text became the transport. So the
 * one check that would have settled it was believed impossible, and the LSP's message ("the project will not
 * compile until it is replaced with a real operand") went unverified.
 *
 * It is TRUE — measured live on CODESYS SP21, each shape pushed into a fixture project and built:
 *
 *   instance position   `??? : TON(IN := a, PT := t);`   4 errors, build fails
 *                       ("Expression expected instead of '?'", "Program name, function or function block
 *                        instance expected instead of '!!!'ERROR'!!!'", "Unexpected token '?' found")
 *   assignment target   `??? := a;`                      "The assignment target is not specified."
 *   target behind EN    `IF en1 THEN ??? := NOT(a); …`   the same, plus two about the implicit temp
 *
 * So the LSP and the compiler agree that every one of these is an error, and these fixtures hold them to it
 * ON THE TEXT, not merely on the fact that both flagged something. The check reads which SLOT the marker sits
 * in and emits the compiler's own wording for it:
 *
 *   operand / input pin / unnamed instance   Expression expected instead of '?'
 *   assignment target (incl. behind an EN)   The assignment target is not specified.
 *
 * It emits ONE per marker where the compiler's parser sometimes emits two to four. That is deliberate and it
 * is a SUBSET, never an invention: the corpus gate forbids two diagnostics sharing a (range, code), the extra
 * messages are parse-recovery noise, and one of them names an implicit temp (`__FB__ImpVar15`) whose number
 * cannot be reproduced offline. These were in `KNOWN_DIVERGENCES` while the LSP answered every position with
 * one invented sentence; they are not any more.
 * * WHAT THIS DOES NOT COVER, and what measuring it established. `Lenze_MID-S100` builds with ZERO errors
 * while four of these markers sit in two of its POUs (`Mach1_MIDS`, `AHWF`) that Volt's reachability calls
 * LIVE. The LSP reports them; the compiler does not; and the reason is NOT that either is wrong about the
 * marker — it is that the compiler never looked.
 *
 * MEASURED (SP21, scripts/audit-check.ts with VOLT_NO_INSTANTIATE): the SAME POU, `??? := a;`, answers
 * `The assignment target is not specified.` when it is instantiated in PLC_PRG and answers NOTHING when it
 * is not — build success and all. CODESYS generates code only for what it can reach, so an object nothing
 * reaches is not checked at all, whatever is wrong inside it.
 *
 * That mechanism is proven; which instance of it applies to those two POUs is NOT yet settled, and the
 * evidence cuts both ways: `AHWF` is called behind an UNCONNECTED enable (`LET en1 := ; IF en1 THEN AHWF();
 * END_IF`), so that call plainly generates nothing — but `Mach1_MIDS` is called from `General`, a real task
 * root, with a WIRED enable, which should compile it. What tips it is where the build's own six warnings
 * come from: `MotionControl/Lenze/` only, and not one from the `A70_MachineModuleSources` subtree that holds
 * all four markers. So that whole subtree looks unbuilt, which points back at exclude-from-build (CODESYS
 * has a FOLDER-level control — `ScriptBuildProperties.FolderController`) rather than at reachability.
 *
 * Either way the conclusion for the LSP is the same, and it is why these fixtures matter: the four are a
 * MEASUREMENT gap, not a precision one. Volt cannot see what the compiler skipped, so `build-conformance`
 * cannot subset against it. See `packages/volt-cli/scripts/probe-exclude-from-build.py`.
 */
import type { LanguageTest } from "../types.js"

export const NETWORK_UNRESOLVED_TESTS: readonly LanguageTest[] = [
  {
    name: "network_unnamed_instance",
    pouName: "FB_LANG_network_unnamed_instance",
    kind: "function_block",
    feature: "`???` in a call box's INSTANCE position",
    fromDoc: "network-text.md#the-one-instance-that-carries-its-own-type",
    note: "The shape Lenze_MID-S100's `MotionControl/POU` holds four of. Network text spells the type inline here (`??? : TYPE(…)`) because `???` is declared nowhere for the push to read it from.",
    plcPrgVar: "fb_nui : FB_LANG_network_unnamed_instance;",
    plcPrgBody: "fb_nui();",
    source: `FUNCTION_BLOCK FB_LANG_network_unnamed_instance
VAR
\ta : BOOL;
\tt : TIME;
END_VAR

NETWORK 0 FBD
  ??? : TON(IN := a, PT := t);
END_NETWORK

END_FUNCTION_BLOCK
`,
  },
  {
    name: "network_unnamed_assignment_target",
    pouName: "FB_LANG_network_unnamed_target",
    kind: "function_block",
    feature: "`???` as an assignment TARGET (a coil / outVariable nobody named)",
    fromDoc: "network-text.md#sink--lvalue--operand",
    note: "CODESYS answers `The assignment target is not specified.` — a different error from the instance case, which is why both shapes are held here rather than one standing in for the other.",
    plcPrgVar: "fb_nut : FB_LANG_network_unnamed_target;",
    plcPrgBody: "fb_nut();",
    source: `FUNCTION_BLOCK FB_LANG_network_unnamed_target
VAR
\ta : BOOL;
END_VAR

NETWORK 0 LD
  ??? := a;
END_NETWORK

END_FUNCTION_BLOCK
`,
  },
  {
    name: "network_unnamed_target_behind_enable",
    pouName: "FB_LANG_network_unnamed_target_en",
    kind: "function_block",
    feature: "`???` as an assignment target inside an UNCONNECTED enable",
    fromDoc: "network-text.md#eneno--let-en--src-if-en-then-result-end_if",
    note: "The exact shape the two LIVE Lenze POUs carry, and the reason it is here: an unconnected EN does NOT excuse the marker — the compiler still errors. That rules out 'the rung is not generated' as the explanation for those POUs building clean, leaving exclude-from-build.",
    plcPrgVar: "fb_nute : FB_LANG_network_unnamed_target_en;",
    plcPrgBody: "fb_nute();",
    source: `FUNCTION_BLOCK FB_LANG_network_unnamed_target_en
VAR
\ta : BOOL;
END_VAR

NETWORK 0 LD
  LET en1 := ;
  IF en1 THEN ??? := NOT(a); END_IF
END_NETWORK

END_FUNCTION_BLOCK
`,
  },
  {
    name: "network_unnamed_input_pin",
    pouName: "FB_LANG_network_unnamed_input_pin",
    kind: "function_block",
    feature: "`???` on a NAMED INPUT pin of an FB call",
    fromDoc: "network-text.md#fb-instance-call--instpin--arg--and-output-read-instpin",
    note: "The position NO real project has shown us yet — pinned because 'never seen' is not 'cannot happen'. Same two parse errors as an operand: the compiler chokes on the marker text wherever it stands.",
    plcPrgVar: "fb_nip : FB_LANG_network_unnamed_input_pin;",
    plcPrgBody: "fb_nip();",
    source: `FUNCTION_BLOCK FB_LANG_network_unnamed_input_pin
VAR
	t1 : TON;
	pt : TIME;
END_VAR

NETWORK 0 FBD
  t1(IN := ???, PT := pt);
END_NETWORK

END_FUNCTION_BLOCK
`,
  },
  {
    name: "network_unnamed_group_operand",
    pouName: "FB_LANG_network_unnamed_group_operand",
    kind: "function_block",
    feature: "`???` as an operand inside a group",
    fromDoc: "network-text.md#operator-group---operand-op-operand-",
    note: "The marker where a plain variable belongs. Grouped with the pin case because the compiler answers both identically — which is itself the finding: position matters for the TARGET case and nowhere else.",
    plcPrgVar: "fb_ngo : FB_LANG_network_unnamed_group_operand;",
    plcPrgBody: "fb_ngo();",
    source: `FUNCTION_BLOCK FB_LANG_network_unnamed_group_operand
VAR
	a : BOOL;
	out : BOOL;
END_VAR

NETWORK 0 FBD
  out := (??? AND a);
END_NETWORK

END_FUNCTION_BLOCK
`,
  },
]
