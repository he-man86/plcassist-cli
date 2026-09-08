using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Volt.Engine.Format.St;
using Volt.Engine.Item;
using Xunit;

namespace Volt.Engine.Tests;

/// <summary>
/// EVERY FIELD OF <see cref="ItemContent"/> SURVIVES THE FORMAT, AND A NEW FIELD CANNOT BE ADDED WITHOUT
/// SAYING SO HERE.
///
/// <para><b>Three separate bugs in one session had one shape</b>: a field the vendor stores, that Volt's model
/// can hold, that something along the way quietly did not carry — an accessor's <c>VAR END_VAR</c> declaration,
/// a coil's edge and negation bits, a task call entry's comment.</para>
///
/// <para><b>Be exact about what this gate does and does not reach, because over-claiming coverage is how the
/// next one gets through.</b> Those three were dropped at the VENDOR boundary
/// (<c>AccessorDeclaration.Keep</c>, <c>NetworkTextWriter.AssignOp</c>, <c>RebuildCallList</c>) — above the
/// drivers, where only a live IDE can be the oracle, which is why all three needed a probe. This file gates the
/// FORMAT boundary: a field that reaches <see cref="ItemContent"/> intact and is then lost by
/// <see cref="StWriter"/> or <see cref="StReader"/>. Same failure shape, different seam, and the one seam that
/// can be gated offline. (Verified by breaking <c>AssembleAccessor</c> to drop a declaration: this test goes
/// red, which is the only evidence that it is a gate and not decoration.)</para>
///
/// <para><b>And it is the half <c>StFixedPointTests</c> cannot see.</b> That one starts from TEXT and proves
/// <c>Write(Read(x)) == x</c> — necessary, and blind to a field the writer never emits, because the reader then
/// never produces it either and the two agree perfectly about nothing. Starting from a fully-populated MODEL is
/// what makes an unemitted field visible.</para>
///
/// <para><b>And the reflection half is the part that survives us.</b> Asserting the round trip on a fixture
/// only covers the fields someone remembered to put in the fixture. So the fixture is checked AGAINST THE
/// RECORD: every property of <see cref="ItemContent"/>, <see cref="Member"/> and <see cref="Accessor"/> must be
/// set to a distinctive non-default value, and adding a field to any of them fails this test until it is either
/// carried through the format or listed as a documented exception. Same principle as <c>bun run check</c> —
/// a contract that is declared in more than one place cannot be extended in only one of them.</para>
/// </summary>
public class ItemContentIsFullyCarriedTests
{
    /// <summary>Fields that legitimately do not round-trip, each with the reason. The list is deliberately
    /// short and deliberately hard to grow: an entry here is a claim that the FORMAT cannot carry the field,
    /// not that carrying it was inconvenient.</summary>
    private static readonly Dictionary<string, string> NotCarried = new()
    {
        [$"{nameof(Member)}.{nameof(Member.ReturnType)}"] =
            "WRITE-only and vendor-driven: TwinCAT wants an interface member's type as the create's vInfo. The " +
            "reader DERIVES it from the declaration rather than carrying it, so it is not a field the text lost.",
        [$"{nameof(Member)}.{nameof(Member.DataType)}"] =
            "Same as ReturnType — derived from the declaration by the reader, never stored in the text.",
    };

    /// <summary>An item with every field of every record populated, each value distinct enough that a swap or a
    /// drop is visible. Trailing newlines are deliberately absent: the format joins parts with one, so a
    /// trailing newline is the one thing it genuinely cannot carry (see <c>AccessorDeclaration.Keep</c>).</summary>
    private static ItemContent Maximal() => new(
        Kind: ItemKind.Kinds.FunctionBlock,
        Declaration: "FUNCTION_BLOCK FB_Everything\nVAR\n\tnCount : INT := 7;\nEND_VAR",
        Body: "nCount := nCount + 1;",
        Members: new List<Member>
        {
            new(Kind: ItemKind.Kinds.Method,
                Name: "DoWork",
                Declaration: "METHOD PUBLIC DoWork : BOOL\nVAR_INPUT\n\tbGo : BOOL;\nEND_VAR",
                Body: "DoWork := bGo;",
                Folder: "Internals",
                ReturnType: "BOOL"),
            new(Kind: ItemKind.Kinds.Property,
                Name: "Level",
                Declaration: "PROPERTY PUBLIC Level : INT",
                Body: null,
                Folder: "Exposed",
                // Both accessors present, with DIFFERENT declarations — the exact asymmetry that made the
                // dropped getter declaration visible to a human reader in the first place.
                Getter: new Accessor("VAR\nEND_VAR", "Level := nCount;"),
                Setter: new Accessor("PRIVATE\nVAR\nEND_VAR", "nCount := Level;"),
                DataType: "INT"),
        });

    // ── the reflection half ────────────────────────────────────────────────────────────────────────────────

    /// <summary>Every property of the three records is populated by <see cref="Maximal"/>. Adding a field to
    /// <see cref="ItemContent"/>, <see cref="Member"/> or <see cref="Accessor"/> fails HERE, before it can fail
    /// silently in production by never being written.</summary>
    [Fact]
    public void The_fixture_populates_every_field_the_records_declare()
    {
        var item = Maximal();
        var covered = new HashSet<string>(StringComparer.Ordinal);

        // AGGREGATED across the fixture, never per instance: a METHOD legitimately has no accessors and a
        // PROPERTY legitimately has no body, so "default on this object" is not "the fixture never exercises
        // it". Asking per instance made this fail on a correct fixture.
        Cover(typeof(ItemContent), item, nameof(ItemContent), covered);
        foreach (var m in item.Members) Cover(typeof(Member), m, nameof(Member), covered);
        foreach (var a in item.Members.SelectMany(m => new[] { m.Getter, m.Setter }).Where(a => a is not null))
            Cover(typeof(Accessor), a!, nameof(Accessor), covered);

        var unset = Declared().Where(f => !covered.Contains(f) && !NotCarried.ContainsKey(f)).ToList();

        Assert.True(unset.Count == 0,
            "These fields exist on the content records and the fixture leaves them at their default, so nothing " +
            "in this file proves they are carried:\n  " + string.Join("\n  ", unset.Distinct()) +
            "\nPopulate them in Maximal(), or add them to NotCarried with the reason the format cannot hold them.");
    }

    private static void Cover(Type t, object instance, string label, HashSet<string> covered)
    {
        foreach (var p in Fields(t))
        {
            var v = p.GetValue(instance);
            var isDefault = v is null
                            || (v is string s && s.Length == 0)
                            || (v is System.Collections.ICollection c && c.Count == 0);
            if (!isDefault) covered.Add($"{label}.{p.Name}");
        }
    }

    /// <summary>Every property that is genuinely a FIELD OF THE MODEL. A record's compiler-generated
    /// <c>EqualityContract</c> is not one, and <c>Accessor.Code</c> is derived from <c>Body</c> with no storage
    /// of its own — carrying it separately would be carrying the same fact twice.</summary>
    private static IEnumerable<PropertyInfo> Fields(Type t) =>
        t.GetProperties(BindingFlags.Public | BindingFlags.Instance)
         .Where(p => p.Name != "EqualityContract")
         .Where(p => !(t == typeof(Accessor) && p.Name == nameof(Accessor.Code)));

    private static IEnumerable<string> Declared() =>
        new[] { typeof(ItemContent), typeof(Member), typeof(Accessor) }
            .SelectMany(t => Fields(t).Select(p => $"{t.Name}.{p.Name}"));

    // ── the round-trip half ────────────────────────────────────────────────────────────────────────────────

    /// <summary>THE GATE. A fully-populated model, written and read back, is the same model — field by field,
    /// so a failure names what was lost instead of dumping two blobs.</summary>
    [Fact]
    public void Every_populated_field_survives_write_then_read()
    {
        var before = Maximal();
        var after = StReader.Read(StWriter.Write(before));

        Assert.Equal(before.Kind, after.Kind);
        Assert.Equal(before.Declaration, after.Declaration);
        Assert.Equal(before.Body, after.Body);
        Assert.Equal(before.Members.Select(m => m.Name), after.Members.Select(m => m.Name));

        foreach (var (b, a) in before.Members.Zip(after.Members))
        {
            Assert.Equal(b.Kind, a.Kind);
            Assert.Equal(b.Name, a.Name);
            Assert.Equal(b.Declaration, a.Declaration);
            Assert.Equal(b.Folder, a.Folder);

            // A PROPERTY has no body in ST — there is no syntax for one between `PROPERTY x : T` and its
            // accessors — so `null` and `""` are the same absence there and the format carries neither. That
            // is a fact about the LANGUAGE, not a thing this layer dropped, and it is the only reason the
            // comparison is normalised. Everything with a real body is compared exactly, below.
            if (b.Kind is ItemKind.Kinds.Property or ItemKind.Kinds.InterfaceProperty)
                Assert.Equal(b.Body ?? "", a.Body ?? "");
            else
                Assert.Equal(b.Body, a.Body);
            AssertAccessor(b.Name + ".Getter", b.Getter, a.Getter);
            AssertAccessor(b.Name + ".Setter", b.Setter, a.Setter);
        }
    }

    private static void AssertAccessor(string what, Accessor? before, Accessor? after)
    {
        // Presence IS the object: null means "no such accessor", and a push of null REMOVES it. Conflating
        // null with an empty accessor is how a getter gets silently deleted, so the null-ness is asserted
        // before anything inside it.
        Assert.True(before is null == after is null, $"{what}: presence changed across the round trip");
        if (before is null) return;

        Assert.Equal(before.Declaration, after!.Declaration);
        Assert.Equal(before.Body, after.Body);
    }

    /// <summary>A body that EXISTS is preserved to the character, null stays null and empty stays empty.
    ///
    /// <para>The distinction is load-bearing below the seam: both drivers write a member's implementation on
    /// <c>!= null</c>, so <c>null</c> means "leave the body alone" and <c>""</c> means "clear it". TwinCAT
    /// skipped empty implementations once and emptied bodies stopped being cleared — a real data-loss bug. A
    /// format that collapsed the two would reintroduce it from above.</para></summary>
    [Theory]
    [InlineData("DoWork := bGo;")]
    [InlineData("")]
    public void A_members_own_body_keeps_its_exact_value(string body)
    {
        var before = new ItemContent(
            ItemKind.Kinds.FunctionBlock,
            "FUNCTION_BLOCK FB_B\nVAR\nEND_VAR",
            "n := 1;",
            new List<Member>
            {
                new(ItemKind.Kinds.Method, "DoWork",
                    "METHOD PUBLIC DoWork : BOOL\nVAR_INPUT\n\tbGo : BOOL;\nEND_VAR", body),
            });

        var after = StReader.Read(StWriter.Write(before));

        Assert.Equal(body, Assert.Single(after.Members).Body);
    }

    /// <summary>The exception list is not a place to park a field: every entry must name a property that still
    /// exists. A renamed or deleted field leaves a stale excuse behind, and a stale excuse is how the next
    /// field gets waved through.</summary>
    [Fact]
    public void Every_documented_exception_still_names_a_real_field()
    {
        var known = Declared().ToHashSet(StringComparer.Ordinal);

        foreach (var key in NotCarried.Keys)
            Assert.True(known.Contains(key), $"NotCarried lists '{key}', which no content record declares.");
    }
}
