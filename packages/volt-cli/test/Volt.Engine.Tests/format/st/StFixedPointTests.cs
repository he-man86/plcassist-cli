using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Xunit;
using Volt.Engine.Format.St;
using Volt.Engine.Item;

namespace Volt.Engine.Tests;

/// <summary>
/// <b>THE ROUND-TRIP INVARIANT: what a pull writes, a push must be able to send back unchanged.</b>
///
/// <para>A workspace file is <see cref="StWriter"/>'s output, and a push feeds it straight back through
/// <see cref="StReader"/>. So <c>Write(Read(x)) == x</c> is not a nicety — it IS the guarantee that pulling a
/// project and pushing it again is a no-op, and every byte the pair disagrees on is a byte an engineer's project
/// silently loses or gains. This gate holds the WHOLE emitted text to the file, not a field of it, because the
/// failures below were all boundary whitespace: no assertion about a declaration's content would have seen one
/// of them.</para>
///
/// <para><b>Why one gate instead of a test per bug.</b> These fixtures are the shapes a sweep of five real
/// customer projects turned up — 55 files across 902 that Volt could not take its own output back from. They
/// are not six independent defects; they are six faces of one thing, that the declaration/implementation
/// boundary is IMPLICIT in the file and both sides have to agree on where it is. A new emitter rule or reader
/// rule that gets any face wrong fails here, including the faces nobody has hit yet — which is what a per-bug
/// test cannot do. When a live corpus turns up a seventh shape, it belongs in this folder, not in a new class.</para>
///
/// <para>Sweeping real projects is still worth doing and is NOT a build-agent job (the corpora are large and
/// live outside volt-cli): set <c>VOLT_CORPUS</c> to `packages/volt-lsp-iec/test-corpus` and
/// <see cref="Every_file_in_a_real_corpus_survives_a_round_trip"/> runs the same assertion over all of them.</para>
/// </summary>
public class StFixedPointTests
{
    private static readonly string FixtureDir =
        Path.Combine(AppContext.BaseDirectory, "fixtures", "st-fixed-point");

    public static TheoryData<string> Fixtures()
    {
        var data = new TheoryData<string>();
        foreach (var f in Directory.GetFiles(FixtureDir).OrderBy(f => f, StringComparer.Ordinal))
            data.Add(Path.GetFileName(f));
        return data;
    }

    [Theory]
    [MemberData(nameof(Fixtures))]
    public void A_pulled_file_reads_and_writes_back_byte_for_byte(string fixture)
    {
        var text = Read(Path.Combine(FixtureDir, fixture));
        Assert.Equal(text, StWriter.Write(StReader.Read(text)));
    }

    /// <summary>The boundary is implicit, so the two sides have to agree on it TWICE — once about where the
    /// declaration ends, once about which blank lines are separator. This pins the first half directly: text a
    /// human would call "the header" must come back as the DECLARATION, never as executable code. A function
    /// block whose base class lands in its body still round-trips as text; it stops being a derived function
    /// block in the IDE, which is the failure the byte comparison alone cannot describe.</summary>
    [Fact]
    public void A_wrapped_header_is_declaration_not_body()
    {
        var item = StReader.Read(Read(Path.Combine(FixtureDir, "wrapped-header-no-var-section.fb")));

        Assert.Contains("EXTENDS Cylinder_52ValveFB", item.Declaration);
        Assert.Contains("IMPLEMENTS IActuator", item.Declaration);
        Assert.DoesNotContain("EXTENDS", item.Body ?? "");
        Assert.DoesNotContain("IMPLEMENTS", item.Body ?? "");
    }

    /// <summary>The other half: a member's leading documentation belongs to the MEMBER. `IModuleBase` kept a
    /// 23-line usage example on the interface itself because the walk that claims a member's trivia could not
    /// see that ` *)` closes a comment opened twenty lines earlier.</summary>
    [Fact]
    public void A_block_comment_above_a_member_belongs_to_that_member()
    {
        var item = StReader.Read(Read(Path.Combine(FixtureDir, "block-comment-with-a-blank-line-above-a-member.itf")));

        var eStop = item.Members.Single(m => m.Name == "EStop");
        Assert.Contains("Add code here to handle emergency stops", eStop.Declaration);
        Assert.DoesNotContain("Add code here to handle emergency stops", item.Declaration);
        // …and the interface's own wrapped header stays where it belongs.
        Assert.Contains("EXTENDS IAbleToRegister", item.Declaration);
    }

    /// <summary>The sweep, over whatever `VOLT_CORPUS` points at. Skipped — not failed — when it is unset, which
    /// is every CI run: a corpus is a real customer project and cannot be committed here.</summary>
    [Fact]
    public void Every_file_in_a_real_corpus_survives_a_round_trip()
    {
        var corpus = Environment.GetEnvironmentVariable("VOLT_CORPUS");
        if (string.IsNullOrEmpty(corpus) || !Directory.Exists(corpus)) return;

        var drifted = new List<string>();
        var checkedCount = 0;
        foreach (var file in Directory.EnumerateFiles(corpus, "*.*", SearchOption.AllDirectories))
        {
            // A referenced library's signatures carry source extensions but are RENDERED, not pulled — they are
            // read-only by location and never travel back through a push.
            if (file.Contains("Library Manager", StringComparison.Ordinal)) continue;
            var ext = Path.GetExtension(file).TrimStart('.').ToLowerInvariant();
            if (!ItemKind.IsSourceKind(ItemKind.KindForWireName("x." + ext) ?? "")) continue;

            var text = Read(file);
            checkedCount++;
            string back;
            try { back = StWriter.Write(StReader.Read(text)); }
            catch (Exception ex) { drifted.Add($"{file}: THREW {ex.Message}"); continue; }
            if (back != text) drifted.Add($"{file}: {FirstDifference(text, back)}");
        }

        Assert.True(checkedCount > 0, $"VOLT_CORPUS='{corpus}' holds no source files — wrong directory?");
        Assert.Empty(drifted);
    }

    /// <summary>Workspace files are LF; a checkout on Windows may smudge them to CRLF (`.gitattributes` says
    /// `text=auto`), and the format under test is defined in LF. Normalising here keeps the gate about the
    /// format rather than about the checkout.</summary>
    private static string Read(string path) => File.ReadAllText(path).Replace("\r\n", "\n");

    private static string FirstDifference(string want, string got)
    {
        var a = want.Split('\n');
        var b = got.Split('\n');
        for (var i = 0; i < Math.Max(a.Length, b.Length); i++)
            if (i >= a.Length || i >= b.Length || a[i] != b[i])
                return $"line {i + 1} want {Quote(i < a.Length ? a[i] : null)} got {Quote(i < b.Length ? b[i] : null)}";
        return "(identical line by line — the trailing newline differs)";
    }

    private static string Quote(string? line) => line is null ? "<eof>" : "\"" + line + "\"";
}
