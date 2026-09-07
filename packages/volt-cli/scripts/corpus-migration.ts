/**
 * CORPUS MIGRATION — a GAP FINDER, not a gate.
 *
 * It pushes a real customer project into an EMPTY one and materializes the result back, so every item is a
 * CREATE: folders, kinds, children, graphical bodies, the lot. `test/e2e/whole-project.test.ts` pushes a
 * project's own bytes back over ITSELF and therefore only ever exercises the UPDATE path; this finds what that
 * cannot. It is also the operation a user actually performs — migrating a machine builder's project into a
 * fresh one — which is why the oracle is a real project rather than a shape Volt authored.
 *
 * **Nothing here is a permanent test.** The corpora are big, slow and live outside `volt-cli`, and running them
 * proves nothing on a build agent. Their job is to SURFACE gaps; every gap this finds gets a dedicated,
 * offline test in `volt-cli` that fails without the fix, and THAT is the standing coverage. The first run
 * produced `Volt.Engine.Tests/sync/CreateUnauthorableBodyTests.cs` — the create path wrote a CFC/SFC body
 * marker as if it were source and landed an EMPTY function block, with the push reporting success.
 *
 * WHAT IS COMPARED. Writable source only (`SOURCE_EXTENSIONS` + folder markers), because that is all a push may
 * carry: library signatures, device/task descriptors and project settings belong to the TARGET project, and a
 * blank one legitimately has different ones. Paths are normalized on the device-root segment (`Device` in every
 * corpus, `PLCWinNT` in the CODESYS blank template) so the comparison is about structure, not about what the
 * target's controller happens to be called.
 *
 * WHAT IS NOT MIGRATABLE, AND WHY THAT IS NOT A FINDING. A CFC/SFC/IL body has no text form at all — its file
 * carries a `(* @volt-graphical: LANG *)` marker instead of source — so there is nothing to create it FROM.
 * Those are counted and reported, never staged; pushing one is refused by `BodyFormatGuard`.
 *
 * RUNNING IT. It owns the IDE lifecycle: a throwaway blank project is opened per corpus and closed again, so no
 * bridge should be running when it starts.
 *
 *   bun run scripts/corpus-migration.ts                 # every corpus
 *   bun run scripts/corpus-migration.ts pro2193         # one
 *
 * Budget ~5-20 min per corpus; pro2193 and lenze-mid are ~8k items each. Exits non-zero when anything drifted.
 */
import { execFileSync } from "node:child_process"
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, join, relative, sep } from "node:path"
import { SOURCE_EXTENSIONS } from "@volt/control"

const REPO = join(import.meta.dir, "..", "..", "..")
const VOLT = join(REPO, "packages", "volt-cli", "src", "Volt.Cli", "bin", "Release", "net8.0", "volt.exe")
const CORPUS_ROOT = join(REPO, "packages", "volt-lsp-iec", "test-corpus")
const LAUNCHER = join(import.meta.dir, "codesys-pipe.ps1")

/** The device-root segment, replaced by this placeholder on both sides so a corpus harvested from `Device`
 *  can be compared against a blank project whose controller is `PLCWinNT`. */
const DEV = "<device>"
/** A referenced library's files carry SOURCE extensions but are read-only by LOCATION — the push refuses them
 *  and the blank target has different libraries anyway. Excluded by folder, exactly as the CLI does. */
const LIBRARY_DIR = "Library Manager"
const FOLDER_MARKER = ".gitkeep"
/** A body with no text form — CFC, SFC, IL. The file carries this instead of source. */
const BODY_MARKER = "(* @volt-graphical:"

const VENDOR = process.env.VOLT_VENDOR ?? "codesys"

// ── vendor lifecycle: open a BLANK project, serve it, close it ────────────────────────────────────────────

interface Blank {
	/** Opens a throwaway empty project and blocks until its pipe serves. */
	open(label: string): void
	close(): void
}

const CODESYS: Blank = {
	open(label) {
		// A COPY of the shipped template, per corpus — never a committed fixture, and never twice over the same
		// file: the point is that the target starts empty every single time.
		const scratch = mkdtempSync(join(tmpdir(), `volt-blank-${label}-`))
		const project = join(scratch, "Blank.project")
		copyFileSync(join(codesysInstall(), "CODESYS", "Templates", "Standard.project"), project)
		ps(LAUNCHER, ["-Action", "up", "-NoBuild", "-Project", project])
		waitForPipe()
	},
	close() {
		ps(LAUNCHER, ["-Action", "down"])
	},
}

// TwinCAT has no headless mode and no in-proc host (see test/e2e/README.md), so its blank has to be opened
// through `twincat-instances.ps1` against an empty solution. Not wired yet — this refuses rather than skipping
// quietly, because a silent skip is how a vendor stays untested through a whole implementation.
const BLANKS: Record<string, Blank> = { codesys: CODESYS }

function codesysInstall(): string {
	const dir = "C:\\Program Files\\CODESYS 3.5.21.40"
	if (!existsSync(dir)) throw new Error(`CODESYS SP21 not found at ${dir}`)
	return dir
}

/** The host serves `volt.bridge.<vendor>.<pid>`; wait for any pipe under the vendor prefix. */
function waitForPipe(timeoutMs = 300_000): void {
	const prefix = `volt.bridge.${VENDOR}.`
	const deadline = Date.now() + timeoutMs
	while (Date.now() < deadline) {
		if (readdirSync("\\\\.\\pipe\\").some((p) => p.startsWith(prefix))) return
		Bun.sleepSync(2000)
	}
	throw new Error(`no ${prefix}* pipe after ${timeoutMs / 1000}s — did the IDE fail to open the blank project?`)
}

function ps(script: string, args: string[]): string {
	return execFileSync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, ...args], {
		encoding: "utf8",
		maxBuffer: 64 * 1024 * 1024,
	})
}

/** `volt`, with the CLI's own stdout/stderr preserved on failure — a refused push says WHY, and that message is
 *  the finding, not noise to be swallowed by an exec error. */
function volt(cwd: string, args: string[]): string {
	try {
		return execFileSync(VOLT, args, { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 })
	} catch (err) {
		const e = err as { stdout?: string; stderr?: string }
		throw new Error(`volt ${args.join(" ")} failed:\n${e.stdout ?? ""}\n${e.stderr ?? ""}`.trim())
	}
}

/** A fresh workspace materialized from whatever the bridge currently serves. */
function initWorkspace(label: string): { root: string; src: string; dispose: () => void } {
	const tmp = mkdtempSync(join(tmpdir(), `volt-${label}-`))
	volt(tmp, ["init", "--vendor", VENDOR])
	const created = readdirSync(tmp, { withFileTypes: true }).filter((e) => e.isDirectory())
	if (created.length !== 1) throw new Error(`expected one workspace under ${tmp}, found ${created.length}`)
	const root = join(tmp, created[0]!.name)
	return { root, src: join(root, "src"), dispose: () => rmSync(tmp, { recursive: true, force: true, maxRetries: 3 }) }
}

// ── the tree under comparison ─────────────────────────────────────────────────────────────────────────────

/** The single top-level directory holding `Plc Logic` — the controller, whatever it is named. */
function deviceRoot(root: string): string {
	const hit = readdirSync(root, { withFileTypes: true }).filter(
		(e) => e.isDirectory() && existsSync(join(root, e.name, "Plc Logic")),
	)
	if (hit.length !== 1) throw new Error(`expected exactly one device root under ${root}, found ${hit.length}`)
	return hit[0]!.name
}

function isSource(name: string): boolean {
	const dot = name.lastIndexOf(".")
	return dot >= 0 && SOURCE_EXTENSIONS.has(name.slice(dot + 1).toLowerCase())
}

/**
 * Every pushable file under `root`, keyed by its device-normalized relative path. Library signatures are
 * dropped by folder (read-only by location) and reference manifests by extension.
 */
function pushableTree(root: string): Map<string, string> {
	const device = deviceRoot(root)
	const out = new Map<string, string>()
	const walk = (dir: string): void => {
		for (const e of readdirSync(dir, { withFileTypes: true })) {
			if (e.isDirectory()) {
				if (e.name !== LIBRARY_DIR) walk(join(dir, e.name))
			} else if (isSource(e.name) || e.name === FOLDER_MARKER) {
				const path = join(dir, e.name)
				const rel = relative(root, path).split(sep).join("/")
				out.set(rel.startsWith(device + "/") ? DEV + rel.slice(device.length) : rel, readFileSync(path, "utf8"))
			}
		}
	}
	walk(root)
	return out
}

/** Lay the staged files into the workspace, removing any the workspace has and the set does not — so one push
 *  exercises create, update AND delete, which is what a real migration does. */
function stage(files: Map<string, string>, srcRoot: string): void {
	const device = deviceRoot(srcRoot)
	const abs = (rel: string): string => join(srcRoot, rel.replace(DEV, device).split("/").join(sep))
	for (const rel of pushableTree(srcRoot).keys()) if (!files.has(rel)) rmSync(abs(rel))
	for (const [rel, text] of files) {
		const path = abs(rel)
		mkdirSync(dirname(path), { recursive: true })
		writeFileSync(path, text)
	}
}

/** A readable report: what is missing, what is extra, and the first line that differs. */
function diff(expected: Map<string, string>, actual: Map<string, string>): string[] {
	const problems: string[] = []
	for (const [rel, want] of expected) {
		const got = actual.get(rel)
		if (got === undefined) problems.push(`${rel}: MISSING — did not survive the migration`)
		else if (got !== want) problems.push(`${rel}: DRIFTED\n${firstDifference(want, got)}`)
	}
	for (const rel of actual.keys()) if (!expected.has(rel)) problems.push(`${rel}: EXTRA — not in the corpus`)
	return problems
}

function firstDifference(want: string, got: string): string {
	const a = want.split("\n")
	const b = got.split("\n")
	for (let i = 0; i < Math.max(a.length, b.length); i++)
		if (a[i] !== b[i])
			return `    line ${i + 1}\n      want: ${JSON.stringify(a[i])}\n      got:  ${JSON.stringify(b[i])}`
	return "    (lines identical — the trailing newline differs)"
}

// ── one corpus, end to end ────────────────────────────────────────────────────────────────────────────────

function migrate(name: string): string[] {
	const blank = BLANKS[VENDOR]
	if (!blank) throw new Error(`no blank-project launcher for '${VENDOR}' — CODESYS only for now`)

	const all = pushableTree(join(CORPUS_ROOT, name))
	if (all.size === 0) throw new Error(`${name} has no pushable source — is the corpus stale?`)
	const staged = new Map([...all].filter(([, text]) => !text.includes(BODY_MARKER)))
	const unauthorable = all.size - staged.size

	console.log(`\n── ${name}: ${staged.size} file(s) to migrate${unauthorable ? `, ${unauthorable} unauthorable (CFC/SFC/IL)` : ""}`)

	blank.open(name)
	const pusher = initWorkspace(`push-${name}`)
	try {
		stage(staged, pusher.src)
		volt(pusher.root, ["push"])

		// A SECOND workspace, so what comes back is a materialization and never a merge. A `volt pull` back into
		// the pusher would be a git merge, so a genuine reshape shows up as a CONFLICT rather than a readable
		// diff — which hides the one thing this is looking for.
		const reader = initWorkspace(`read-${name}`)
		try {
			return diff(staged, pushableTree(reader.src))
		} finally {
			reader.dispose()
		}
	} finally {
		pusher.dispose()
		blank.close()
	}
}

// ── main ──────────────────────────────────────────────────────────────────────────────────────────────────

const only = process.argv[2]
const corpora = readdirSync(CORPUS_ROOT, { withFileTypes: true })
	.filter((e) => e.isDirectory() && (!only || e.name === only))
	.map((e) => e.name)
if (corpora.length === 0) throw new Error(`no corpus matching '${only}' under ${CORPUS_ROOT}`)

const findings = new Map<string, string[]>()
for (const name of corpora) {
	try {
		findings.set(name, migrate(name))
	} catch (err) {
		findings.set(name, [`the migration itself failed: ${err instanceof Error ? err.message : String(err)}`])
	}
}

console.log("\n══ corpus migration ══")
let total = 0
for (const [name, problems] of findings) {
	total += problems.length
	console.log(`  ${problems.length === 0 ? "OK  " : "GAP "} ${name.padEnd(22)} ${problems.length} problem(s)`)
}
for (const [name, problems] of findings) {
	if (problems.length === 0) continue
	console.log(`\n── ${name} — first ${Math.min(40, problems.length)} of ${problems.length}`)
	for (const p of problems.slice(0, 40)) console.log(`  ${p}`)
}
console.log(
	total === 0
		? "\nevery corpus migrated into a blank project unchanged."
		: `\n${total} problem(s). Each one is a GAP: fix it, then add a test to volt-cli that fails without the fix.`,
)
process.exit(total === 0 ? 0 : 1)
