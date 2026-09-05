/**
 * SHARED TEST FIXTURES for `@volt/control`.
 *
 * <p>A workspace is "bound" when `.git/volt/config.json` exists — that file is the whole of the binding, and
 * nearly every test here needs one. Five files each carried their own copy of the four lines that write it
 * (`cli-args`, `connector` twice, `reconnect`, `session`, and the connector e2e), with gratuitous differences:
 * one wrote only the vendor, one wrote vendor + project, one hardcoded `codesys`/`"P"`, and each invented its own
 * temp-directory prefix. There was no `test-support` module to put it in, so every new test file added a sixth.</p>
 *
 * <p>One builder instead, with the shape as parameters. It matters beyond tidiness: the binding file's LAYOUT is
 * a contract with the CLI (`.git/volt`, `bridge.vendor`, `project.platform`, `project.projectName`), and six
 * hand-written copies is six places to update when it moves — five of which nobody would remember.</p>
 */
import { mkdirSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

/** A unique temp directory. Never reused, so tests cannot see each other's bindings. */
export function tempDir(prefix = "volt-test"): string {
	const dir = join(tmpdir(), `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`)
	mkdirSync(dir, { recursive: true })
	return dir
}

/**
 * A workspace directory bound to a vendor, and optionally to a named project.
 *
 * <p>Vendor-only is a REAL state, not a shorthand: `volt init --vendor` binds the workspace to a bridge before any
 * project is picked, and the connect picker exists precisely for that moment. Passing a `projectName` produces the
 * fully-bound state that per-workspace status resolves against.</p>
 */
export function boundWorkspace(
	opts: { vendor?: string; projectName?: string; prefix?: string } = {},
): string {
	const dir = tempDir(opts.prefix ?? "volt-ws")
	if (opts.vendor === undefined) return dir // an UNBOUND workspace — no config file at all
	mkdirSync(join(dir, ".git", "volt"), { recursive: true })
	const config: Record<string, unknown> = { bridge: { vendor: opts.vendor } }
	if (opts.projectName !== undefined) config.project = { platform: opts.vendor, projectName: opts.projectName }
	writeFileSync(join(dir, ".git", "volt", "config.json"), JSON.stringify(config))
	return dir
}
