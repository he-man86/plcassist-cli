using Volt.Engine.Format.Network;
using Xunit;

namespace Volt.Engine.Tests.Format.Network;

/// <summary>
/// A COIL MODIFIER THE TEXT FORM CANNOT SPELL MUST NOT COME OUT AS A PLAIN COIL.
///
/// <para><c>AssignOp</c> renders a target's storage — <c>:=</c> / <c>S=</c> / <c>R=</c> — and nothing else, but
/// <c>ReadTarget</c> carries three more bits onto that same target: <see cref="Flags.Negated"/> (the fourth
/// coil kind, <c>Negation</c> without <c>Set</c>) and <see cref="Flags.Rising"/> / <see cref="Flags.Falling"/>
/// (the vendor's <c>Rtrig</c>/<c>Ftrig</c>, the Edge Detection command applied to a coil output, spelled
/// <c>&lt;coil edge="rising"&gt;</c> in PLCopen). All three rendered as an ordinary <c>:=</c>.</para>
///
/// <para><b>Nothing downstream could have caught it.</b> The fixed-point gate is text → model → text, so it
/// only ever sees what the PULL already wrote; a flag dropped before the text exists is absent from both sides
/// of every comparison and re-emits identically forever. <c>NetworkTextGate</c> is the same shape. This is the
/// reset-coil bug's twin — that one inverted 128 coils in one real project and showed up in no diff, because
/// the text Volt wrote was self-consistent.</para>
///
/// <para><b>The measurement that chose the fix.</b> <c>scripts/probe-nwl-coil-modifiers.py</c> censused every
/// assignment target in five real customer projects — 576 targets across 48 graphical POUs and 427 networks,
/// including the 34-ladder Lenze project — and found <b>none</b> of the three. So the hole is latent rather
/// than active, and inventing syntax for a construct that occurs zero times would be a guess. The marker is
/// the answer this codebase already gives for "no editable text form" (CFC, SFC, IL): the engineer is TOLD,
/// instead of being handed a body that silently means something else.</para>
/// </summary>
public class UnspellableCoilTests
{
    private static NetworkBody Body(params Node[] trees) =>
        new(BodyLanguage.Ld, new[] { new Volt.Engine.Format.Network.Network(0, null, null, null, false, trees) });

    private static Node CoilAssign(Flags targetFlags) =>
        new Assign(new Leaf(new Operand("a"), Flags.None),
                   new[] { new Operand("out", IsLValue: true, Flags: targetFlags) },
                   Flags.None);

    [Theory]
    [InlineData(nameof(Flags.Negated), "negated coil")]
    [InlineData(nameof(Flags.Rising), "rising-edge coil")]
    [InlineData(nameof(Flags.Falling), "falling-edge coil")]
    public void A_coil_modifier_with_no_text_form_is_named_rather_than_dropped(string bit, string expected)
    {
        var flags = bit switch
        {
            nameof(Flags.Negated) => Flags.None with { Negated = true },
            nameof(Flags.Rising) => Flags.None with { Rising = true },
            _ => Flags.None with { Falling = true },
        };

        // THE REGRESSION. Before the guard this returned null and the body rendered as `out := a;` — a plain
        // coil, in the engineer's own file, with no signal anywhere that the edge or the negation was gone.
        Assert.Equal($"LD ({expected})", NetworkTextWriter.Unspellable(Body(CoilAssign(flags))));
    }

    /// <summary>The three storage kinds ARE spelled, and must not be swept up by the guard: a project made
    /// entirely of set and reset coils has to keep materializing as text. Lenze's 246 of them are the case.</summary>
    [Theory]
    [InlineData(false, false)]   // plain coil    ->  :=
    [InlineData(true, false)]    // set coil      ->  S=
    [InlineData(false, true)]    // reset coil    ->  R=
    public void A_storage_kind_the_operator_already_spells_is_not_refused(bool set, bool reset)
    {
        Assert.Null(NetworkTextWriter.Unspellable(Body(CoilAssign(Flags.None with { Set = set, Reset = reset }))));
    }

    /// <summary>Control flow is spelled too — by the control-flow path, not by <c>AssignOp</c> — so a
    /// <c>Return</c> target must survive. This is not hypothetical: the census found exactly one, on Lenze's
    /// <c>ATD_FQI</c>, and it round-trips as <c>IF ioAxis.xVirtual THEN RETURN; END_IF</c>. A guard that
    /// refused every unrendered bit would have turned a working ladder POU into a marker.</summary>
    [Fact]
    public void A_return_target_is_not_refused()
    {
        Assert.Null(NetworkTextWriter.Unspellable(Body(CoilAssign(Flags.None with { Return = true }))));
    }

    /// <summary>The walk reaches every node kind, not just a top-level assignment. A ladder buries its coils
    /// under parallels, demuxes and box inputs; a guard that only looked at the root would pass the project it
    /// exists for.</summary>
    [Fact]
    public void The_walk_reaches_a_coil_nested_under_ld_structure()
    {
        var buried = new Volt.Engine.Format.Network.Parallel(
            null,
            new Node[] { new Demux(7, CoilAssign(Flags.None with { Rising = true }), Flags.None) },
            Flags.None);

        Assert.Equal("LD (rising-edge coil)", NetworkTextWriter.Unspellable(Body(buried)));
    }

    /// <summary>A body with nothing exotic in it answers null, so the guard costs nothing on the ordinary
    /// path — every graphical POU in all five corpus projects takes this branch.</summary>
    [Fact]
    public void An_ordinary_body_is_spellable()
    {
        Assert.Null(NetworkTextWriter.Unspellable(Body(CoilAssign(Flags.None))));
    }
}
