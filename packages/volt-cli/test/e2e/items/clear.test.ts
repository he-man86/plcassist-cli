/**
 * Data-integrity: emptying or removing a sub-element CLEARS it in the IDE — no stale content survives.
 *
 * This is the class the TwinCAT empty-body bug lived in: `WriteText` skipped an empty implementation, so
 * an emptied body/method/accessor kept its OLD content (silent data loss; CODESYS cleared correctly). The
 * fix writes on `implementation != null`, and PushService passes null only for slot-less kinds. These cases
 * lock that behaviour in on BOTH bridges (the POU-body case lives in endpoints/fetch.test.ts).
 *
 * <p>SCOPE: emptying content, not REMOVING a child. Two tests here deleted a METHOD and a property SET accessor
 * on fixtures identical to `children-cycle.test.ts`'s, with strictly weaker assertions (regex instead of
 * substring, and no compile check). Child deletion is that file's subject; this one is about what happens when
 * the child STAYS and its body goes to empty.</p>
 */
import { describe, it, expect, beforeAll, beforeEach, afterEach, afterAll, setDefaultTimeout } from "bun:test"
import { id, fid, cleanup, requireHealthy, createItem, updateItem, fetchSource, savePlcPrg, restorePlcPrg, fixPlcPrg, BASE } from "../harness"
import { fb, METHOD, ACTION } from "../fixtures"

describe(`lifecycle / clear-on-empty (${BASE})`, () => {
	setDefaultTimeout(60_000)
	beforeAll(async () => { await requireHealthy() })
	beforeEach(async () => { await fixPlcPrg(); await cleanup(); await savePlcPrg() })
	afterEach(async () => { await restorePlcPrg() })
	afterAll(cleanup)

	it("emptying a METHOD body clears it", async () => {
		const n = id("c_meth")
		await createItem(fid("c_meth"), fb(n, { children: METHOD("Run", "Run := d + 1;") }))
		await updateItem(fid("c_meth"), fb(n, { children: METHOD("Run", "") }))
		expect(await fetchSource(fid("c_meth"))).not.toMatch(/Run := d \+ 1/)
	})

	it("emptying an ACTION body clears it", async () => {
		const n = id("c_act")
		await createItem(fid("c_act"), fb(n, { children: ACTION("Act", "x := 9;") }))
		await updateItem(fid("c_act"), fb(n, { children: ACTION("Act", "") }))
		expect(await fetchSource(fid("c_act"))).not.toMatch(/x := 9/)
	})

	it("removing a variable from the VAR section clears it from the declaration", async () => {
		const n = id("c_rmvar")
		await createItem(fid("c_rmvar"), fb(n, { vars: "VAR\n\tx : INT;\n\tgone : BOOL;\nEND_VAR", body: "x := 1;" }))
		await updateItem(fid("c_rmvar"), fb(n, { vars: "VAR\n\tx : INT;\nEND_VAR", body: "x := 1;" }))
		expect(await fetchSource(fid("c_rmvar"))).not.toMatch(/gone : BOOL/)
	})
})
