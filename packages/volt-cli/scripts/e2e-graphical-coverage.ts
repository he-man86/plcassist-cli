/**
 * WHICH NETWORK-TEXT CONSTRUCTS DOES THE LIVE SUITE ACTUALLY PUSH?
 *
 * The e2e suite is thorough about the constructs it knows: labels, jumps, returns, titles, EN/ENO, fan-out,
 * Execute boxes, each asserted on CREATE, on the FIXED POINT, and against a real BUILD. What it could not tell
 * anyone is what it has never pushed AT ALL — and that is the shape of every bug it has missed.
 *
 * It missed one. `ladderLabel.prg`, pulled from a real TwinCAT project, is two networks: one holding a coil
 * with nothing driving it (`coil := ;`) and one holding NOTHING but a label. Pushed back into an empty
 * project it came back gutted — declaration gone, LD turned to FBD, both labels gone, one network gone —
 * with `volt push` reporting success (`twincat-graphical-create-loss`). Neither shape appears anywhere in
 * `test/e2e`, so 175 passing tests on both vendors said nothing about either.
 *
 * So this counts. Each construct the FORMAT defines (`docs/network-text.md` section 6, plus the network
 * metadata in section 7) against the e2e sources that push it. It is a REPORT, not a gate: a construct with
 * no coverage is a question — "can this be created, and does anyone know?" — and answering it needs a live
 * IDE, not a red CI job.
 *
 *   bun run scripts/e2e-graphical-coverage.ts
 */
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"

const E2E = join(import.meta.dir, "..", "test", "e2e")

/**
 * WHERE A BODY LINE STARTS, inside a JS source file.
 *
 * The suite builds bodies as SINGLE-LINE string literals in which a newline is the two-character escape
 * `\\n`, not a real one — so a regex anchored with `^` anchors to the start of a SOURCE line and almost never
 * to the start of a body line. That is not a nitpick: it is why the first run of this reported
 * "network COMMENT" as uncovered when `comments.test.ts` pushes two of them. A body line begins at the start
 * of the file, immediately after a `\\n` escape, or immediately after the quote that opens the literal.
 */
const AT_LINE = '(?:^|\\\\n|[\\x22\\x27\\x60])\\s*'

const line = (rest: string): RegExp => new RegExp(AT_LINE + rest, 'm')

/** Every construct the format defines, and how it appears in a pushed body. */
const CONSTRUCTS: { name: string; where: string; match: RegExp }[] = [
	{ name: "wire definition (LET)", where: "§6", match: /\bLET\s+\w+\s*:=/ },
	{ name: "sink (lvalue := operand)", where: "§6", match: line("\\w[\\w.]*\\s*:=\\s*[^;\\s]") },
	{ name: "operator group", where: "§6", match: /:=\s*\([^)]*\b(AND|OR|XOR|ADD|MUL|SUB|DIV)\b/ },
	{ name: "function call", where: "§6", match: /:=\s*[A-Z_]\w*\(/ },
	{ name: "FB instance call", where: "§6", match: /\b\w+\((\w+\s*:=|\s*\))/ },
	{ name: "output read (inst.Pin)", where: "§6", match: /:=\s*\w+\.\w+/ },
	{ name: "unnamed instance (??? : TYPE)", where: "§6", match: /\?\?\?\s*:\s*\w+\(/ },
	{ name: "output pin (=>)", where: "§6", match: /=>/ },
	{ name: "EN/ENO (IF en THEN … END_IF)", where: "§6", match: /IF\s+\w+\s+THEN\b/ },
	{ name: "Execute box", where: "§6", match: /\bEXECUTE\b/ },
	{ name: "modifier NOT", where: "§6", match: /:=\s*NOT\s|\bAND\s+NOT\b|\bOR\s+NOT\b/ },
	{ name: "modifier RISING", where: "§6", match: /\bRISING\b/ },
	{ name: "modifier FALLING", where: "§6", match: /\bFALLING\b/ },
	{ name: "SET coil (S=)", where: "§6", match: /\sS=\s/ },
	{ name: "RESET coil (R=)", where: "§6", match: /\sR=\s/ },
	{ name: "JMP", where: "§6", match: /\bJMP\s+\w+/ },
	{ name: "RETURN", where: "§6", match: /\bRETURN\s*;/ },
	{ name: "network LABEL", where: "§7", match: /NETWORK\s+\d+\s+\w+\s+LABEL:/ },
	{ name: "network TITLE", where: "§7", match: /TITLE:/ },
	{ name: "network COMMENT", where: "§7", match: line("\\/\\/ ") },
	{ name: "network DISABLED", where: "§7", match: /\bDISABLED\b/ },
	{ name: "language LD", where: "§7", match: /NETWORK\s+\d+\s+LD\b/ },
	{ name: "language FBD", where: "§7", match: /NETWORK\s+\d+\s+FBD\b/ },

	// THE TWO THAT WERE MISSING, and the reason this file exists. Both are shapes a real project holds and
	// nothing in the suite creates.
	{ name: "EMPTY network (marker straight to END_NETWORK)", where: "§7", match: /NETWORK\s+\d+\s+\w+[^\n\\]*\\n\s*END_NETWORK/ },
	{ name: "undriven coil (x := ;)", where: "§4", match: line("\\w[\\w.]*\\s*:=\\s*;") },
]

function sources(dir: string): string[] {
	const out: string[] = []
	for (const e of readdirSync(dir)) {
		const p = join(dir, e)
		if (statSync(p).isDirectory()) out.push(...sources(p))
		else if (e.endsWith(".ts")) out.push(p)
	}
	return out
}

/**
 * Only text that is PUSHED counts, so a construct named in PROSE does not read as covered — `labels.test.ts`
 * discusses `coil := ;` in a doc comment while never pushing one, which is exactly the false positive that
 * would have hidden this gap.
 *
 * So JS COMMENT lines are dropped and everything else is kept. The first cut kept only lines containing
 * `NETWORK`, `:=` or `=>`, which was too aggressive in the other direction: a body's own `// network comment`
 * line and a bare `EXECUTE` line contain none of those, so two constructs the suite genuinely covers were
 * reported as gaps. A coverage report that invents gaps is as useless as one that misses them.
 */
function pushedBodies(file: string): string {
	return readFileSync(file, "utf8")
		.split("\n")
		.filter((l) => !/^\s*(\*|\/\/)/.test(l))
		.join("\n")
}

const files = sources(E2E)
const corpus = new Map(files.map((f) => [f, pushedBodies(f)]))

const rows = CONSTRUCTS.map((c) => {
	const hits = [...corpus].filter(([, body]) => c.match.test(body)).map(([f]) => f)
	return { ...c, hits }
})

const covered = rows.filter((r) => r.hits.length > 0)
const missing = rows.filter((r) => r.hits.length === 0)

console.log(`\n══ network-text constructs pushed by test/e2e (${files.length} source files) ══\n`)
for (const r of covered) console.log(`  ok    ${r.where}  ${r.name.padEnd(46)} ${r.hits.length} file(s)`)
console.log()
for (const r of missing) console.log(`  GAP   ${r.where}  ${r.name}`)

console.log(
	`\n${covered.length} of ${rows.length} constructs are pushed somewhere in the live suite; ` +
		`${missing.length} are not pushed at all.\n`,
)
console.log("A GAP is not a failing test — it is a construct nobody has ever asked a live IDE to create.")
console.log("That is what `ladderLabel.prg` was: two shapes no test pushed, and both lost on a real migration.\n")
