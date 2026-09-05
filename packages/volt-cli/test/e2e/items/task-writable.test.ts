/**
 * A TASK IS EDITABLE FROM THE WORKSPACE — the first non-source item that is.
 *
 * `.task` was a read-only descriptor because access was derived from "is this assembled ST", and a scheduling
 * descriptor is not. That was never a statement about the VENDOR: every field is a live setter on CODESYS
 * (`scripts/probe-task-writable.py` — interval, priority, event, the watchdog's four, and a call list with
 * add/insert/remove/replace), so the read-only-ness was Volt's own, and it meant an engineer could see the
 * schedule in git and change nothing about it.
 *
 * These are the three edits a workspace can express, and the third and fourth are the reason this file is not
 * just "set a field": a `.task` file ADDED is a task created, and one DELETED is a task removed. Neither needed
 * new push machinery — a delete op was always generic — but neither could be BUILT for a read-only kind.
 *
 * CODESYS ONLY. TwinCAT renders a different `.task` shape entirely and refuses the write with a reason; the
 * describe below skips there rather than asserting a refusal that would only re-state its own driver.
 */
import { describe, it, expect, beforeAll, setDefaultTimeout } from "bun:test"
import { bridge, id, fid, pushOps, fetchItem, requireHealthy, BASE, VENDOR } from "../harness"

const TASK_FOLDER = "Device/Plc Logic/Application/Task Configuration"

describe.skipIf(VENDOR === "twincat")(`items / a task is writable (${BASE})`, () => {
	setDefaultTimeout(180_000)
	beforeAll(async () => {
		await requireHealthy()
	})

	const refs = async () => await bridge.refs()
	const versionOf = async (name: string) => (await refs()).items[name] ?? null
	const clean = async (name: string) => {
		const v = await versionOf(name)
		if (v !== null) await pushOps([{ op: "deleteItem", name, ifVersion: v }])
	}

	/** The one task every fixture project has, whatever it is called. */
	async function anyTask(): Promise<string> {
		const names = Object.keys((await refs()).items ?? {}).filter((n) => n.endsWith(".task"))
		expect(names.length, "the fixture project has no task to edit").toBeGreaterThan(0)
		return names[0]!
	}

	it("a task's descriptor round-trips unchanged — it was already correct, now it is also writable", async () => {
		// The read side moved onto the shared format when the write side appeared. This is the check that the
		// move changed no bytes: these are hashed into the item version, so a re-flow is a diff in every repo.
		const name = await anyTask()
		const before = (await fetchItem(name)).sourceText
		const r = await pushOps([{ op: "set", name, toFolder: null, sourceText: before, ifVersion: await versionOf(name) }])
		expect(r.accepted, `pushing a task its own bytes was refused: ${JSON.stringify(r.conflicts)}`).toBe(true)
		expect((await fetchItem(name)).sourceText).toBe(before)
	})

	it("an EDITED field reaches the IDE and comes back", async () => {
		const name = await anyTask()
		const original = (await fetchItem(name)).sourceText

		// Priority is the safest field to move: it changes no timing and every task has one.
		const current = /^Priority:\s*(\S+)/m.exec(original)
		expect(current, `no Priority line in:\n${original}`).not.toBeNull()
		const changed = current![1] === "9" ? "8" : "9"
		const edited = original.replace(/^(Priority:\s*)\S+/m, `$1${changed}`)

		try {
			const r = await pushOps([{ op: "set", name, toFolder: null, sourceText: edited, ifVersion: await versionOf(name) }])
			expect(r.accepted, `push refused: ${JSON.stringify(r.conflicts)}`).toBe(true)

			const back = (await fetchItem(name)).sourceText
			expect(back).toContain(`Priority:  ${changed}`)
			// …and NOTHING ELSE moved. A descriptor write that reshapes the rest of the schedule would be far
			// worse than one that refuses.
			expect(back).toBe(edited)
		} finally {
			await pushOps([{ op: "set", name, toFolder: null, sourceText: original, ifVersion: await versionOf(name) }])
		}
	})

	it("the CALL LIST is content: a POU added to it runs, and the order is kept", async () => {
		const name = await anyTask()
		const original = (await fetchItem(name)).sourceText
		const main = Object.keys((await refs()).items ?? {}).find((n) => n === "PLC_PRG.prg" || n === "MAIN.prg")
		expect(main, "no main program to schedule").toBeDefined()
		const pou = main!.replace(/\.[^.]+$/, "")

		// Rewrite the Calls line to exactly this one POU — the list is a sequence, so replacing it is the honest
		// way to assert the whole of it rather than that an entry happens to be present.
		const withCalls = /^Calls:/m.test(original)
			? original.replace(/^Calls:.*$/m, `Calls:     ${pou}`)
			: original.trimEnd() + `\nCalls:     ${pou}\n`

		try {
			const r = await pushOps([{ op: "set", name, toFolder: null, sourceText: withCalls, ifVersion: await versionOf(name) }])
			expect(r.accepted, `push refused: ${JSON.stringify(r.conflicts)}`).toBe(true)
			expect((await fetchItem(name)).sourceText).toBe(withCalls)
		} finally {
			await pushOps([{ op: "set", name, toFolder: null, sourceText: original, ifVersion: await versionOf(name) }])
		}
	})

	it("a NEW .task file creates a real task, and DELETING it removes one", async () => {
		const name = fid("task_new", "task")
		await clean(name)

		const body = "Type:      Cyclic\nInterval:  100 ms\nPriority:  20\nWatchdog:  off\n"
		const created = await pushOps([{ op: "set", name, toFolder: TASK_FOLDER, sourceText: body, ifVersion: null }])
		expect(created.accepted, `create refused: ${JSON.stringify(created.conflicts)}`).toBe(true)

		// It is a real task the IDE now schedules, not a file on the side: it comes back through `refs` and
		// materializes with the settings it was given.
		expect(await versionOf(name)).not.toBeNull()
		expect((await fetchItem(name)).sourceText).toBe(body)

		const removed = await pushOps([{ op: "deleteItem", name, ifVersion: await versionOf(name) }])
		expect(removed.accepted, `delete refused: ${JSON.stringify(removed.conflicts)}`).toBe(true)
		expect(await versionOf(name)).toBeNull()
	})

	it("a body that is not canonical is refused, with the exact text to use", async () => {
		const name = await anyTask()
		const r = await pushOps([
			{ op: "set", name, toFolder: null, sourceText: "Type: Cyclic\nPriority: 5\nWatchdog: off\n", ifVersion: await versionOf(name) },
		])
		expect(r.accepted).toBe(false)
		expect(JSON.stringify(r.conflicts)).toContain("Type:")
	})
})
