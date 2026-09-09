using System.Collections.Generic;
using System.Linq;
using Volt.Contracts;
using Volt.Engine.Item;
using Volt.Engine.Sync;
using Xunit;

namespace Volt.Engine.Tests;

/// <summary>
/// THE BATCH PRE-FLIGHT SEES A PROPERTY'S ACCESSOR BODIES.
///
/// <para>A push is all-or-nothing for the class of refusal that is decidable from the source TEXT — that is the
/// whole reason <c>ValidateSourceOrThrow</c> runs over every op before the first write, and
/// <c>A_batch_refused_on_a_LATER_op_writes_NONE_of_the_earlier_ones</c> asserts it. Non-canonical network text
/// is squarely in that class: <c>NetworkTextGate.Validate</c> needs no IDE.</para>
///
/// <para><b>It walked past every accessor.</b> A property's code lives in its GET/SET, not in a body of its own
/// — <c>StReader.ReadProperty</c> gives the member <c>Body: ""</c> and puts the text in
/// <c>Getter</c>/<c>Setter</c> — and the pre-flight enumerated <c>split.Body</c> and <c>m.Body</c> only. So a
/// hand-edited, non-canonical FBD GET body passed pre-flight, and was refused for the FIRST time from inside
/// the driver's write (<c>CodesysDriver.WriteAccessor</c> / <c>BeckhoffDriver.Collect</c>) — after every
/// earlier op of the same push had already been committed to the live IDE, and those are not rolled back.</para>
///
/// <para>The sibling create-path guard <c>BodyFormatGuard.RequireAuthorable</c> already splits members exactly
/// this way, with a comment saying why. This one simply never got it.</para>
/// </summary>
public class AccessorPreflightTests
{
    /// <summary>Canonical FBD — what a pull produces, and what the gate accepts unchanged.</summary>
    private const string Canonical = "NETWORK 0 FBD\n  out := a;\nEND_NETWORK";

    /// <summary>The same network with a redundant hand-added wire. It PARSES — so only the canonical check
    /// catches it — and the writer inlines the single use, so it would drift on the very next pull. Both forms
    /// were measured against the gate rather than assumed: a genuinely NAMED wire like `g7` IS canonical and
    /// survives, which is why this uses the auto-minted `i1` spelling the writer collapses.</summary>
    private const string NonCanonical = "NETWORK 0 FBD\n  LET i1 := a;\n  out := i1;\nEND_NETWORK";

    private static string Fb(string name, string accessorBody) =>
        $"FUNCTION_BLOCK {name}\nVAR\n\ta : BOOL;\n\tout : BOOL;\nEND_VAR\n\nEND_FUNCTION_BLOCK\n\n" +
        $"PROPERTY Ready : BOOL\nGET\n{accessorBody}\nEND_GET\nEND_PROPERTY\n";

    private static string Prg(string name) => $"PROGRAM {name}\nVAR\nEND_VAR\n\nn := 0;\n\nEND_PROGRAM\n";

    private static PushResponse Push(FakeIde ide, params PushOp[] ops)
    {
        var refs = RefsService.Handle(ide);
        return PushService.Handle(ide, new PushRequest
        {
            ExpectedProjectVersion = refs.ProjectVersion,
            Ops = ops.ToList(),
        });
    }

    private static SetItemOp Set(string wireName, string src) =>
        new() { Name = wireName, SourceText = src, IfVersion = null };

    /// <summary>THE REGRESSION. The bad accessor is on the SECOND op, so nothing may reach the IDE at all —
    /// the earlier op is the one the pre-flight exists to protect.</summary>
    [Fact]
    public void A_non_canonical_GET_body_is_refused_before_the_first_write()
    {
        var ide = new FakeIde();

        var res = Push(ide, Set("First.prg", Prg("First")), Set("FB_Axis.fb", Fb("FB_Axis", NonCanonical)));

        Assert.False(res.Accepted);
        Assert.Empty(ide.CreatedItems);
        Assert.Empty(ide.WrittenContent);
    }

    /// <summary>The complement — the same push with a CANONICAL accessor body lands. Without this the test
    /// above would pass on a pre-flight that refused every property.</summary>
    [Fact]
    public void A_canonical_GET_body_still_pushes()
    {
        var ide = new FakeIde();

        var res = Push(ide, Set("First.prg", Prg("First")), Set("FB_Axis.fb", Fb("FB_Axis", Canonical)));

        Assert.True(res.Accepted, "push refused: " + (res.Conflicts is null
            ? "(none)"
            : string.Join(" | ", res.Conflicts.Select(c => c.Reason))));
        Assert.Contains("FB_Axis", ide.CreatedItems);
    }

    /// <summary>And a SET body is gated too — the setter is a separate field and was equally invisible.</summary>
    [Fact]
    public void A_non_canonical_SET_body_is_refused_before_the_first_write()
    {
        var ide = new FakeIde();
        var src = "FUNCTION_BLOCK FB_Axis\nVAR\n\ta : BOOL;\n\tout : BOOL;\nEND_VAR\n\nEND_FUNCTION_BLOCK\n\n" +
                  $"PROPERTY Ready : BOOL\nSET\n{NonCanonical}\nEND_SET\nEND_PROPERTY\n";

        var res = Push(ide, Set("First.prg", Prg("First")), Set("FB_Axis.fb", src));

        Assert.False(res.Accepted);
        Assert.Empty(ide.CreatedItems);
    }
}
