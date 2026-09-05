using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Xunit;

namespace Volt.Repo.Gates;

/// <summary>
/// BOTH VENDORS DO THE SAME THINGS — and where they do not, the build says so out loud.
///
/// <para><b>The repo already gates parity of SHAPE and had nothing for parity of CAPABILITY.</b>
/// <c>VendorParityGuardTests</c> forbids a vendor literal in the engine, <c>EndpointParityTests</c> holds
/// /refs, /fetch and the push receipt to one version map, and the e2e <c>vendor-parity</c> suite drives BOTH
/// bridges and compares what they serve. Not one of them would have failed on the change that prompted this:
/// making `.task` writable on CODESYS alone. A workspace file that is editable on one vendor and read-only on
/// the other passed every gate, because every gate was asking whether the two AGREE about an item, never
/// whether they can both DO the same thing to it.</para>
///
/// <para><b>Why that gap is the bad kind.</b> `docs/ITEM_KINDS.md` already lists eighteen vendor-exclusive
/// rows and they are fine: they say a KIND does not exist on that vendor (TwinCAT has parameter lists, CODESYS
/// has traces), so nothing appears in the workspace and there is nothing to be surprised by. A capability gap
/// is the opposite — the same file, in both workspaces, behaving differently — and it is invisible until an
/// engineer edits one and pushes.</para>
///
/// <para><b>So the table below is the declaration, and this gate is what makes it true.</b> Adding a kind to
/// <c>ItemKind.WritableReferenceKinds</c> without a row here fails the build; a row claiming a vendor supports
/// a write while its driver still refuses fails too. The day TwinCAT's task write lands, this test fails and
/// forces the row updated — which is the point: the gap cannot rot quietly, and closing it cannot go
/// unrecorded.</para>
/// </summary>
public class VendorCapabilityParityTests
{
    /// <summary>Which vendors implement the WRITE for each writable non-source kind.
    ///
    /// <para>Source kinds (POUs, DUTs, GVLs, interfaces) are deliberately absent: both drivers have always
    /// written those, and a gap there would break far louder than a gate. This table is for the descriptor
    /// kinds, where writability is a choice each driver makes.</para></summary>
    private static readonly IReadOnlyDictionary<string, VendorSupport> Writable =
        new Dictionary<string, VendorSupport>(StringComparer.Ordinal)
        {
            // A task's schedule is writable on CODESYS — every field is a live setter (DIALECT C19). TwinCAT
            // keeps the same information in a different shape (`Name=` / `linked-task=`, the PLC task being a
            // REFERENCE to a system task that holds the schedule), and which of the two copies the runtime
            // actually honours has not been measured on hardware. Its driver refuses rather than guess, and a
            // write that looked right and scheduled nothing would be the worst of the three outcomes.
            ["task"] = new(Codesys: true, Twincat: false,
                           Why: "TwinCAT's PLC task is a reference to a SYSTEM task; which copy the runtime " +
                                "honours is unmeasured, so its driver refuses the write (ITEM_KINDS.md, DIALECT C19)"),
        };

    private sealed record VendorSupport(bool Codesys, bool Twincat, string Why);

    /// <summary>Every writable reference kind is DECLARED above. A new one cannot arrive unnoticed.</summary>
    [Fact]
    public void Every_writable_reference_kind_declares_its_vendor_support()
    {
        var declared = ReadWritableReferenceKinds();
        var missing = declared.Where(k => !Writable.ContainsKey(k)).ToList();
        Assert.True(missing.Count == 0,
            $"ItemKind.WritableReferenceKinds gained {string.Join(", ", missing)} with no row in this table. " +
            "A kind a push can write is a capability, and a capability that exists on one vendor only is the " +
            "kind of gap this gate exists to keep visible — add the row (and say why, if it is one-sided).");

        var stale = Writable.Keys.Where(k => !declared.Contains(k)).ToList();
        Assert.True(stale.Count == 0,
            $"this table declares {string.Join(", ", stale)}, which ItemKind no longer calls writable — " +
            "remove the row so the table keeps describing the code.");
    }

    /// <summary>A one-sided capability must be VISIBLE where a reader would look: the kind table names it, and
    /// the refusing driver says why in the refusal itself.</summary>
    [Fact]
    public void A_one_sided_capability_is_recorded_where_a_reader_looks()
    {
        foreach (var (kind, support) in Writable.Where(x => x.Value.Codesys != x.Value.Twincat))
        {
            Assert.False(string.IsNullOrWhiteSpace(support.Why),
                $"'{kind}' is writable on one vendor only and the table gives no reason.");

            // The refusing driver must REFUSE — not silently accept and do nothing, which is the failure mode a
            // capability gap actually produces in the field.
            var refusing = support.Codesys ? TwincatDriverDir() : CodesysDriverDir();
            var vendorName = support.Codesys ? "TwinCAT" : "CODESYS";
            var sources = string.Join("\n", Directory.EnumerateFiles(refusing, "*.cs", SearchOption.AllDirectories)
                .Where(NotBuildOutput).Select(File.ReadAllText));
            Assert.True(Regex.IsMatch(sources, @"BridgeErrorCodes\.Unsupported"),
                $"'{kind}' is not supported on {vendorName}, but nothing in its driver refuses with " +
                "BridgeErrorCodes.Unsupported — a capability the driver neither implements nor refuses is one " +
                "that fails somewhere the user cannot read.");
        }
    }

    /// <summary>The one-sided kinds are named in `docs/ITEM_KINDS.md`, which is where someone asking "can I edit
    /// this file?" actually looks — the gate keeps the prose honest rather than replacing it.</summary>
    [Fact]
    public void The_kind_table_documents_every_one_sided_capability()
    {
        var doc = File.ReadAllText(Path.Combine(RepoRoot(), "packages", "volt-cli", "docs", "ITEM_KINDS.md"));
        foreach (var (kind, _) in Writable.Where(x => x.Value.Codesys != x.Value.Twincat))
            Assert.True(doc.Contains($"`{kind}`", StringComparison.Ordinal),
                $"docs/ITEM_KINDS.md does not mention the '{kind}' kind, whose write support differs per vendor.");
    }

    // ── reading the declaration out of the engine ────────────────────────────────────────────────────────

    /// <summary>The kinds `ItemKind.WritableReferenceKinds` lists, read from source. This gate holds no project
    /// reference (it gates the REPO), so the declaration is read the way the sibling gates read theirs.</summary>
    private static IReadOnlyCollection<string> ReadWritableReferenceKinds()
    {
        var itemKind = File.ReadAllText(Path.Combine(
            RepoRoot(), "packages", "volt-cli", "src", "Volt.Engine", "Item", "ItemKind.cs"));

        var decl = Regex.Match(itemKind, @"WritableReferenceKinds\s*=\s*new\[\]\s*\{([^}]*)\}");
        Assert.True(decl.Success,
            "could not find `WritableReferenceKinds = new[] { … }` in ItemKind.cs — this gate reads it as text, " +
            "so a change to its shape has to be reflected here.");

        // `Kinds.Task` → the kind's own string constant, which is the extension-shaped lowercase name.
        var kinds = Regex.Matches(decl.Groups[1].Value, @"Kinds\.(\w+)").Select(m => m.Groups[1].Value).ToList();
        Assert.NotEmpty(kinds);
        return kinds.Select(k => KindConstantValue(itemKind, k)).ToList();
    }

    /// <summary>`Kinds.Task` → "task": the literal the constant is declared with, so the table is keyed by the
    /// name that appears on the wire and in the workspace rather than by a C# identifier.</summary>
    private static string KindConstantValue(string itemKindSource, string constant)
    {
        var m = Regex.Match(itemKindSource, $@"\b{Regex.Escape(constant)}\s*=\s*""([^""]+)""");
        Assert.True(m.Success, $"ItemKind.Kinds.{constant} has no string literal this gate could read");
        return m.Groups[1].Value;
    }

    private static bool NotBuildOutput(string file) =>
        !file.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}") &&
        !file.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}");

    private static string TwincatDriverDir() =>
        Path.Combine(RepoRoot(), "packages", "volt-cli", "src", "Volt.Ide.Twincat");

    private static string CodesysDriverDir() =>
        Path.Combine(RepoRoot(), "packages", "volt-cli", "src", "Volt.Ide.Codesys");

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "packages", "volt-cli", "Volt.sln")))
            dir = dir.Parent;
        Assert.NotNull(dir);
        return dir!.FullName;
    }
}
