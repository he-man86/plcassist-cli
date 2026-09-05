using Volt.Ide.Twincat;
using Xunit;

namespace Volt.Ide.Twincat.Tests;

/// <summary>
/// EMPTYING A BODY CLEARS IT — the regression test for a real data-loss bug that had none.
///
/// <para>TwinCAT's <c>WriteText</c> once guarded its implementation write with <c>!IsNullOrEmpty</c>. An engineer
/// who deleted a POU's body pushed an EMPTY implementation, the guard skipped the write, and the IDE kept the OLD
/// body — silent data loss, and a divergence from CODESYS, whose <c>WriteSourceText</c> writes on
/// <c>implementation != null</c>. The fix was to write on <c>!= null</c> here too.</para>
///
/// <para><b>Nothing pinned that fix on either vendor.</b> None of this suite's doubles modelled a settable body
/// property at all (<c>FakeNode</c>, <c>PouNode</c> and <c>FaultingNode</c> each expose reads), so reverting the
/// guard would have left every offline test green. The distinction the bug turns on is exactly the one asserted
/// below: <c>null</c> means "this kind has no such slot — do not touch it", and <c>""</c> is a real value that
/// must be written.</para>
/// </summary>
public class TcWriteTextTests
{
    /// <summary>A node with both text slots, as a POU has. Plain properties: <c>WriteText</c> reaches them
    /// through <c>dynamic</c>, which binds to a C# class exactly as it binds to the vendor's COM object.</summary>
    /// <para>PUBLIC, and it has to be. `dynamic` resolves members in the CALLING assembly's context — the
    /// driver's — so a private or internal test type binds to nothing there and every write throws
    /// `RuntimeBinderException: 'object' does not contain a definition for ...`. The vendor's real COM object
    /// is public too, so this is the faithful shape rather than a concession.</para>
    public sealed class WritableNode
    {
        public string DeclarationText { get; set; } = "PROGRAM P\nVAR\n\tx : INT;\nEND_VAR";
        public string ImplementationText { get; set; } = "x := 1;";
    }

    [Fact]
    public void An_EMPTY_implementation_is_written_so_an_emptied_body_is_cleared()
    {
        var node = new WritableNode();

        new TcObjectModel().WriteText(node, declaration: null, implementation: "");

        Assert.Equal("", node.ImplementationText);
    }

    [Fact]
    public void A_NULL_implementation_leaves_the_body_alone_because_the_kind_has_no_slot()
    {
        var node = new WritableNode();

        new TcObjectModel().WriteText(node, declaration: null, implementation: null);

        Assert.Equal("x := 1;", node.ImplementationText);
    }

    /// <summary>The same split on the DECLARATION side: an action has no declaration slot (its COM object does not
    /// even expose one), so null must not be written — while an empty declaration is a value like any other.</summary>
    [Fact]
    public void The_declaration_follows_the_same_null_versus_empty_rule()
    {
        var cleared = new WritableNode();
        new TcObjectModel().WriteText(cleared, declaration: "", implementation: null);
        Assert.Equal("", cleared.DeclarationText);

        var untouched = new WritableNode();
        new TcObjectModel().WriteText(untouched, declaration: null, implementation: null);
        Assert.Equal("PROGRAM P\nVAR\n\tx : INT;\nEND_VAR", untouched.DeclarationText);
    }

    [Fact]
    public void Both_slots_are_written_when_both_are_supplied()
    {
        var node = new WritableNode();

        new TcObjectModel().WriteText(node, declaration: "PROGRAM P\nEND_VAR", implementation: "y := 2;");

        Assert.Equal("PROGRAM P\nEND_VAR", node.DeclarationText);
        Assert.Equal("y := 2;", node.ImplementationText);
    }
}
