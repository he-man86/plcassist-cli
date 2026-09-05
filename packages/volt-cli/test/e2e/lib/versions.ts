/**
 * THE HASH SPINE — the three versions the wire publishes (`projectVersion`, `structureVersion`, and one per item)
 * and how they must move.
 *
 * <p>These are what make `volt status` quiet after a no-op and loud after a real edit, so "which of the three
 * changed" IS the contract. Asserting it by hand — `expect(refs2.items[x]).not.toBe(refs1.items[x])` — is how the
 * old suite did it in most places, and it says nothing about the other two.</p>
 */
import { expect } from "bun:test"
import { bridge } from "./bridge"

export type Snapshot = { project: string; structure: string; items: Record<string, string> }

export async function snapshot(): Promise<Snapshot> {
	const r = await bridge.refs()
	return { project: r.projectVersion, structure: r.structureVersion, items: r.items }
}

/** An item's version by FULL wire name, or undefined when absent. */
export function versionIn(s: Snapshot, name: string): string | undefined {
	return s.items[name]
}

export function has(s: Snapshot, name: string): boolean {
	return s.items[name] !== undefined
}

/**
 * Assert how one item and BOTH aggregate versions moved between two snapshots.
 *
 * <p>All three every time, deliberately: the interesting failures are the ones where the item moved correctly and
 * an aggregate did not (a content edit that bumps `structureVersion` makes every client re-walk the tree for
 * nothing; a rename that does not bump it leaves them believing the old layout).</p>
 *
 *   item: "new" | "change" | "same" | "gone"
 *   project / structure: true = must change, false = must stay identical
 */
export function assertDelta(
	before: Snapshot,
	after: Snapshot,
	name: string,
	exp: { item: "new" | "change" | "same" | "gone"; project: boolean; structure: boolean },
): void {
	switch (exp.item) {
		case "new":
			expect(before.items[name], `${name} should not have existed before`).toBeUndefined()
			expect(after.items[name], `${name} should exist after`).toBeDefined()
			break
		case "change":
			expect(after.items[name], `${name} should exist after`).toBeDefined()
			expect(after.items[name], `${name}'s version should have changed`).not.toBe(before.items[name])
			break
		case "same":
			expect(after.items[name], `${name}'s version should NOT have changed`).toBe(before.items[name])
			break
		case "gone":
			expect(before.items[name], `${name} should have existed before`).toBeDefined()
			expect(after.items[name], `${name} should be gone after`).toBeUndefined()
			break
	}
	if (exp.project) expect(after.project, "projectVersion should have changed").not.toBe(before.project)
	else expect(after.project, "projectVersion should NOT have changed").toBe(before.project)
	if (exp.structure) expect(after.structure, "structureVersion should have changed").not.toBe(before.structure)
	else expect(after.structure, "structureVersion should NOT have changed").toBe(before.structure)
}

// ── referenced-library artefacts ──────────────────────────────────────────────

const LIBRARY_EXT = ".library"

/**
 * The library-manager node(s), found as the parent the `.library` refs share.
 *
 * <p>DERIVED FROM THE PAYLOAD, never matched on a folder NAME. Three separate tests each hardcoded
 * `folder.includes("Library Manager")` — CODESYS's name for that node, where TwinCAT calls it `References` — so
 * each silently answered "no libraries here" on the other vendor. That was invisible while TwinCAT shipped no
 * signatures at all; the moment it did, one gate measured nothing and another read all 230 signatures as project
 * items leaking out of a fetch.</p>
 *
 * <p>Anything at or below the node is a library artefact, including the deliberate `(unresolved)` bucket. Pass the
 * `changed` list of a FULL fetch (the one carrying the `.library` refs) — a warm fetch has none and would answer
 * "nothing is a library", which is why callers derive the roots once and reuse them.</p>
 */
export function libraryRoots(changed: readonly any[]): string[] {
	const libFolders = changed
		.filter((i) => String(i.name ?? "").toLowerCase().endsWith(LIBRARY_EXT))
		.map((i) => String(i.folder ?? ""))
	return [...new Set(libFolders.map((f) => (f.includes("/") ? f.slice(0, f.lastIndexOf("/")) : f)))].filter(
		(r) => r.length > 0,
	)
}

/** Whether a folder sits at or below one of {@link libraryRoots}. */
export function inLibrary(folder: string | undefined, roots: readonly string[]): boolean {
	const f = String(folder ?? "")
	return roots.some((r) => f === r || f.startsWith(r + "/"))
}
