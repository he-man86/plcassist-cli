using System.Linq;
using System.Xml.Linq;
using Volt.Engine.Format.Body;
using Volt.Engine.Format.Network;
using Xunit;

namespace Volt.Ide.Twincat.Tests;

/// <summary>
/// WHY THE IMPORTER'S SPLIT CANNOT BE UNDONE — a network's items are all ONE TYPE.
///
/// <para><c>fixtures/tc-pou/importer-split.TcPOU</c> is real XAE output, captured 2026-09-06 by pushing ONE
/// network holding two independent rungs (<c>t1(IN := a, PT := pt); done := t1.Q;</c>) and reading back what the
/// importer built: TWO networks. CODESYS keeps the one, so this was the last divergence in
/// `twincat-graphical-create-parity` that was neither a refusal nor a measured impossibility — it looked like a
/// layout choice waiting for the right repair.</para>
///
/// <para><b>It is not a layout choice. It is forced by the serialization.</b> A network's <c>NetworkItems</c> is
/// a list that declares its element type ONCE, on itself (<c>&lt;l2 cet="BoxTreeAssign"&gt;</c>), and across every
/// committed archive NOT ONE child carries a <c>t</c> of its own. So a network can hold box-rooted trees or
/// assign-rooted trees — never both. Splitting `t1(…)` from `done := t1.Q;` is the only way the vendor can write
/// them down, and one network per connected component (D25) is the CONSEQUENCE of that, not a preference.</para>
///
/// <para><b>Two earlier explanations were wrong, and both were tested before being dropped.</b> The first said a
/// tree in the second network points into the first (`done := ()` after a merge). It does not: that tree is an
/// ordinary assign whose RValue is a plain operand whose text is <c>"t1.Q"</c> — no id, no connector — and the
/// two networks' <c>Id</c>s do not even overlap. The second was the obvious repair from that: stamp each moved
/// item's own <c>t</c> before moving it, since <see cref="TcArchive"/>'s format note says a child's <c>t</c> wins
/// over the list's <c>cet</c>. True OF VOLT'S READER, and not of the vendor's — the merged body round-tripped
/// perfectly through <c>TcNetworkReader</c> offline and came back from a live XAE as <c>done := ();</c>, because
/// TwinCAT's own deserializer types the children from the list. The merge is deleted; this is what it left.</para>
/// </summary>
public class TcImporterSplitTests
{
    private static string Built() =>
        XDocument.Parse(Fixtures.Pou("importer-split.TcPOU"), LoadOptions.PreserveWhitespace)
            .Descendants("NWL").Single().ToString(SaveOptions.DisableFormatting);

    private static XElement Impl(string bodyXml) =>
        XElement.Parse(bodyXml, LoadOptions.PreserveWhitespace)
            .DescendantsAndSelf("o").First(o => (string?)o.Attribute("t") == "NWLImplementationObject");

    /// <summary>The premise: one network in, two networks out. Asserted, so the rest cannot pass vacuously.</summary>
    [Fact]
    public void The_importer_splits_one_pushed_network_into_two()
    {
        var pushed = NetworkTextGate.Validate(
            "NETWORK 0 FBD\n  t1(IN := a, PT := pt);\n  done := t1.Q;\nEND_NETWORK\n");

        Assert.Equal(1, pushed.Networks.Count);
        Assert.Equal(2, TcNetworkReader.Read(Impl(Built()), BodyLanguage.Fbd).Networks.Count);
    }

    /// <summary>AND THE TWO HALVES HAVE DIFFERENT ELEMENT TYPES, which is the reason they are two.
    ///
    /// <para>This is what makes the divergence permanent rather than open: merging them would mean one list
    /// holding both, and the vendor has no way to write that down.</para></summary>
    [Fact]
    public void The_split_networks_carry_different_element_types()
    {
        var lists = Impl(Built()).Descendants("l2")
            .Where(l => (string?)l.Attribute("n") == "NetworkItems")
            .Select(l => (string?)l.Attribute("cet"))
            .ToList();

        Assert.Equal(2, lists.Count);
        Assert.Equal(new[] { "BoxTreeBox", "BoxTreeAssign" }, lists);
    }

    /// <summary>HOW A NETWORK TYPES ITS ITEMS — and it is an EXCLUSIVE OR, not homogeneity.
    ///
    /// <para>This test asserted the wrong rule for a day. Every archive then held said a list declares its
    /// element type once via <c>cet</c> with no child carrying <c>t</c>, so a network looked HOMOGENEOUS and the
    /// importer's split looked permanent. A hand-drawn fan-out (`ladder-demux.TcPOU`) falsified it: that
    /// network's list has NO <c>cet</c> and EVERY child carries its own <c>t</c> —
    /// <c>BoxTreeDemux</c>, <c>BoxTreeAssign</c>, <c>BoxTreeAssign</c>. A network CAN hold mixed item types.</para>
    ///
    /// <para><b>The real contract, across all 22 populated lists here:</b> either <c>cet</c> is present and NO
    /// child has <c>t</c>, or <c>cet</c> is absent and ALL children do. Never a mixture of the two — which is
    /// exactly what the first merge attempt wrote (it kept the destination's <c>cet</c> and stamped <c>t</c> on
    /// only the moved items), and why the vendor read the moved assign as a box and returned
    /// <c>done := ();</c>.</para></summary>
    [Fact]
    public void A_network_types_its_items_by_the_list_or_by_every_child_never_both()
    {
        var violations = new System.Collections.Generic.List<string>();
        var lists = 0;

        foreach (var file in System.IO.Directory.EnumerateFiles(Fixtures.PouDir(), "*.TcPOU"))
        {
            XElement root;
            try { root = XElement.Parse(System.IO.File.ReadAllText(file), LoadOptions.PreserveWhitespace); }
            catch (System.Xml.XmlException) { continue; }

            foreach (var list in root.Descendants("l2").Where(l => (string?)l.Attribute("n") == "NetworkItems"))
            {
                var kids = list.Elements("o").ToList();
                if (kids.Count == 0) continue;
                lists++;

                var cet = (string?)list.Attribute("cet") != null;
                var typed = kids.Count(k => k.Attribute("t") != null);
                var conforms = (cet && typed == 0) || (!cet && typed == kids.Count);
                if (!conforms)
                    violations.Add($"{System.IO.Path.GetFileName(file)}: cet={cet}, {typed}/{kids.Count} children typed");
            }
        }

        Assert.True(lists >= 20, $"only {lists} populated NetworkItems lists — too thin to conclude from");
        Assert.True(violations.Count == 0,
            "a list that is neither fully cet-typed nor fully child-typed — the form the vendor does not write, " +
            "and the one a merge must not produce: " + string.Join(" | ", violations));
    }

    /// <summary>AND A MIXED NETWORK IS A SHAPE THE VENDOR DOES WRITE — the fact that reopens the merge.</summary>
    [Fact]
    public void A_hand_drawn_network_holds_more_than_one_item_type()
    {
        var mixed = XElement.Parse(Fixtures.Pou("ladder-demux.TcPOU"), LoadOptions.PreserveWhitespace)
            .Descendants("l2")
            .Where(l => (string?)l.Attribute("n") == "NetworkItems" && (string?)l.Attribute("cet") == null)
            .Select(l => l.Elements("o").Select(o => (string?)o.Attribute("t")).ToList())
            .FirstOrDefault();

        Assert.NotNull(mixed);
        Assert.True(mixed!.Distinct().Count() > 1, "the child-typed list should hold MORE THAN ONE type");
        Assert.Contains("BoxTreeDemux", mixed);
    }
}
