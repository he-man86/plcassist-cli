using System;
using System.Linq;
using Volt.Contracts;
using Volt.Engine.Item;
using Volt.Engine.Sync;
using Xunit;

namespace Volt.Engine.Tests;

/// <summary>
/// A REFUSED CREATE LEAVES NOTHING BEHIND.
///
/// <para>The create site has always said so — <i>"a refused push must not leave an orphaned, unlisted stub POU
/// behind that blocks the next create"</i> — and it validates the pushed TEXT before creating anything. Text is
/// the half that is knowable up front. TwinCAT's graphical create resolves the body through a PLCopen import,
/// and the importer can return FEWER networks than were pushed, because PLCopen has no element for an empty one
/// (D25). The refusal is correct and it arrives from INSIDE the content write — after the item exists.</para>
///
/// <para><b>Measured on a live XAE.</b> Pushing a two-network LD body whose second network holds only a label
/// was refused with <c>the number of networks changes (1 -&gt; 2)</c>, and left this in the project:</para>
/// <code>
///   PROGRAM VltProbeLadder
///   VAR
///   END_VAR
///
///   NETWORK 0 FBD
///   END_NETWORK
/// </code>
/// <para>An empty shell wearing the engineer's POU name, which the next pull materializes as though they had
/// written it. A corpus migration read that shell back as five separate losses — declaration, language, two
/// labels, a whole network — and it was never a silent success: it was a refusal whose wreckage looked like
/// one. Diagnosing it as data loss cost real time, which is why the shape is pinned here rather than described
/// in a comment.</para>
///
/// <para>An UPDATE is deliberately not rolled back. The item was the engineer's before the push and stays
/// theirs; deleting it because a write failed would be the far worse bug.</para>
/// </summary>
public class CreateRollbackTests
{
    private const string Decl = "FUNCTION_BLOCK FB_New\nVAR\nEND_VAR";
    private const string Source = Decl + "\n\nn := 1;\n\nEND_FUNCTION_BLOCK\n";

    /// <summary>A fake that creates happily and refuses every content write — the shape of the live failure,
    /// where the refusal can only come from the vendor's own import.</summary>
    private static FakeIde Refusing(params FakeIde.Item[] items) =>
        new(items)
        {
            RefuseContentWrite = _ => new BridgeException(
                BridgeErrorCodes.Unsupported,
                "the number of networks changes (1 -> 2), which Volt cannot do through the archive"),
        };

    private static PushResponse Push(FakeIde ide, string name, string source, string? ifVersion)
    {
        var refs = RefsService.Handle(ide);
        return PushService.Handle(ide, new PushRequest
        {
            ExpectedProjectVersion = refs.ProjectVersion,
            Ops = new() { new SetItemOp { Name = name, ToFolder = "", SourceText = source, IfVersion = ifVersion } },
        });
    }

    /// <summary>THE REGRESSION. Before the rollback the item survived its own refusal.</summary>
    [Fact]
    public void An_item_whose_content_write_is_refused_is_not_left_in_the_project()
    {
        var ide = Refusing();

        var res = Push(ide, "FB_New.fb", Source, null);
        Assert.False(res.Accepted, "the push must be refused");

        Assert.False(ide.Exists("FB_New"),
            "the create was rolled back — an item refused on its content must not survive as an empty shell");
    }

    /// <summary>THE REFUSAL IS WHAT REACHES THE ENGINEER, unchanged. A rollback that replaced the vendor's
    /// reason with its own would leave them looking for a mistake in what they pushed.</summary>
    [Fact]
    public void The_original_refusal_survives_the_rollback()
    {
        var ide = Refusing();

        // A refusal is a CONFLICT on the response, not an exception — that is the wire contract, so a push of
        // many ops can report which one failed and why rather than losing the batch to a stack trace.
        var res = Push(ide, "FB_New.fb", Source, null);

        Assert.False(res.Accepted);
        var reason = string.Join(" | ", res.Conflicts.Select(c => c.Reason));
        Assert.Contains("the number of networks changes", reason);
    }

    /// <summary>AN UPDATE IS NEVER ROLLED BACK. The item existed before this push; a failed write leaves it
    /// exactly as it was, and deleting it would turn a refused edit into data loss.</summary>
    [Fact]
    public void An_existing_item_survives_a_refused_write()
    {
        var ide = Refusing(new FakeIde.Item("FB_New", ItemKind.PlcPouFb, "", true, Decl, "n := 0;", null, null));

        var refs = RefsService.Handle(ide);
        var res = Push(ide, "FB_New.fb", Source, refs.Items["FB_New.fb"]);

        Assert.False(res.Accepted, "the write was refused");
        Assert.True(ide.Exists("FB_New"), "a refused UPDATE must leave the engineer's item alone");
    }

    /// <summary>And an ordinary create still lands. A rollback that fired on success would delete every new
    /// item, which is the failure this test exists to make impossible to ship.</summary>
    [Fact]
    public void A_create_that_succeeds_is_untouched()
    {
        var ide = new FakeIde();

        var res = Push(ide, "FB_New.fb", Source, null);

        Assert.True(res.Accepted);
        Assert.True(ide.Exists("FB_New"));
    }
}
