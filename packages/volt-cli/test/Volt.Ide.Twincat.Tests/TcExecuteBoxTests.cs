using System.Linq;
using System.Xml.Linq;
using Volt.Engine.Format.Body;
using Volt.Engine.Format.Network;
using Xunit;

namespace Volt.Ide.Twincat.Tests;

/// <summary>
/// AN EXECUTE BOX, READ FROM REAL VENDOR BYTES.
///
/// <para><c>fixtures/tc-pou/execute-box.TcPOU</c> was DRAWN BY HAND in XAE, because Volt cannot create one on
/// this vendor: emitted as a `&lt;block typeName="EXECUTE"&gt;` the PLCopen importer accepts the push and returns
/// `EXECUTE();` — a plain box whose type name is the string EXECUTE, with the ST gone (DIALECT C20). So this
/// fixture is the only way the shape could be captured, and it joins `VltFixtureCfc`/`VltFixtureSfc` as a
/// hand-authored fixture the suite maintains rather than provisions.</para>
///
/// <para><b>What it is worth.</b> Before it, <c>ReadStCode</c> refused outright — so an engineer who drew an
/// Execute box in their own project could not pull their POU at all. That is a field gap, not a test gap, and it
/// was invisible because no TwinCAT project in this repo contained one.</para>
///
/// <para>Two vendor facts are pinned here, and both were guessable wrongly: the line list is an <c>&lt;a&gt;</c>
/// ARRAY (not the <c>&lt;l2&gt;</c> list every other member uses — read with the wrong accessor it answers EMPTY,
/// which would look like a box with no code), and each line's <c>Text</c> is stored WITH its own surrounding
/// double quotes.</para>
/// </summary>
public class TcExecuteBoxTests
{
    private static string Body() =>
        XDocument.Parse(Fixtures.Pou("execute-box.TcPOU"), LoadOptions.PreserveWhitespace)
            .Descendants("NWL").Single().ToString(SaveOptions.DisableFormatting);

    private static NetworkBody Read() =>
        TcNetworkReader.Read(
            XElement.Parse(Body(), LoadOptions.PreserveWhitespace)
                .DescendantsAndSelf("o").First(o => (string?)o.Attribute("t") == "NWLImplementationObject"),
            BodyLanguage.Fbd);

    [Fact]
    public void The_ST_inside_an_Execute_box_is_read_rather_than_refused()
    {
        var box = Read().Networks
            .SelectMany(n => n.Trees)
            .SelectMany(Flatten)
            .OfType<Box>()
            .Single(b => b.StCode != null);

        // The engineer's line, verbatim — quotes stripped, and NOT the `"iCount:=icount+1;"` the archive stores.
        Assert.Contains("iCount:=icount+1;", box.StCode);
        Assert.DoesNotContain("\"", box.StCode);
    }

    /// <summary>The box carries its ST, so the body materializes with the code rather than as a bare
    /// `EXECUTE();` — which is exactly what the repo shipped before the reader returned null unconditionally.</summary>
    [Fact]
    public void The_body_materializes_with_the_code_not_as_an_empty_call()
    {
        var text = NetworkTextWriter.Write(Read());

        Assert.Contains("EXECUTE", text);
        Assert.Contains("iCount:=icount+1;", text);
        Assert.DoesNotContain("EXECUTE();", text); // the empty-call rendering the old reader produced
    }

    private static System.Collections.Generic.IEnumerable<Node> Flatten(Node n)
    {
        yield return n;
        switch (n)
        {
            case Box b:
                foreach (var i in b.Inputs)
                    foreach (var c in Flatten(i.Value)) yield return c;
                if (b.Enable is { } en) foreach (var c in Flatten(en)) yield return c;
                break;
            case Assign a when a.Value is { } v:
                foreach (var c in Flatten(v)) yield return c;
                break;
            case Volt.Engine.Format.Network.Parallel p:
                if (p.Input is { } pi) foreach (var c in Flatten(pi)) yield return c;
                foreach (var br in p.Branches)
                    foreach (var c in Flatten(br)) yield return c;
                break;
            case Terminator t when t.Input is { } ti:
                foreach (var c in Flatten(ti)) yield return c;
                break;
            case Demux d when d.Input is { } di:
                foreach (var c in Flatten(di)) yield return c;
                break;
        }
    }

    /// <summary>AND EDITING THAT ST FAILS LOUDLY RATHER THAN VANISHING.
    ///
    /// <para>Making the box readable created the edit: an engineer can now pull the POU, change the ST and
    /// push. <c>TcNetworkWriter</c> writes operands, outputs and inputs — never the snippet — so that push
    /// found no storage change, wrote nothing, reported SUCCESS, and the next pull handed the edit back
    /// reverted. Refusing is the fix; writing the lines back needs the <c>TextLine.Id</c> contract measured on
    /// a live XAE first.</para></summary>
    [Fact]
    public void An_edit_to_that_ST_is_refused_rather_than_silently_dropped()
    {
        // Edited the way production edits: through the TEXT, which is what the engineer's file holds.
        var text = NetworkTextWriter.Write(Read()).Replace("iCount:=icount+1;", "iCount:=icount+2;");
        var edited = NetworkTextGate.Validate(text);

        var ex = Assert.ThrowsAny<System.Exception>(() => TcNetworkWriter.Apply(Body(), edited));
        Assert.Contains("ST inside Execute box", ex.Message);
    }

    /// <summary>AND THE DRIVER MUST ACTUALLY REACH THE READER.
    ///
    /// <para>Implementing <c>ReadStCode</c> was not enough on its own: <c>BeckhoffDriver.ReadBody</c> returned
    /// the <c>EXECUTE</c> marker on "does this body contain an Execute box at all", which fired BEFORE the node
    /// walk — so the new reader could not run in production and TwinCAT went on serving a marker where CODESYS
    /// serves network text. Same POU, two different <c>sourceText</c>s, which is what the byte-identical-response
    /// rule forbids. The marker's question is now "is there one I cannot READ".</para>
    ///
    /// <para>Both answers are pinned, because the coarse and precise predicates agree on one fixture and differ
    /// on the other — a test using only the hand-drawn one would pass against the bug.</para></summary>
    [Theory]
    [InlineData("execute-box.TcPOU", false)]        // a real snippet -> readable, so NO marker: read the ST
    [InlineData("ExecuteBox.derived.TcPOU", true)]  // <n n="STSnippet" /> -> no code to show, marker stands
    public void The_marker_asks_whether_the_ST_can_be_read_not_whether_a_box_exists(string fixture, bool marker)
    {
        var impl = TcArchive.Root(
            XDocument.Parse(Fixtures.Pou(fixture), LoadOptions.PreserveWhitespace)
                .Descendants("NWL").Single().ToString(SaveOptions.DisableFormatting));

        Assert.True(Fixtures.HasExecuteBox(impl), $"{fixture} should hold an Execute box at all");
        Assert.Equal(marker, TcArchive.HasUnreadableExecuteBox(impl));
    }
}
