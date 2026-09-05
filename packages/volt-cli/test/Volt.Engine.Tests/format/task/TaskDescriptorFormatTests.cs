using System.Collections.Generic;
using Xunit;
using Volt.Engine.Format.Task;

namespace Volt.Engine.Tests;

/// <summary>
/// The `.task` format, both directions.
///
/// <para>It was a renderer inside the CODESYS driver for as long as `.task` was read-only — no C# test executes
/// that assembly, so the only oracle was a live run. Now that a task can be PUSHED, the two directions are a
/// pair and the round trip is a property that can be proven offline, which is the whole reason the format moved
/// into the engine.</para>
///
/// <para><b>The bodies below are real.</b> They are the exact files `volt pull` produced for the corpus
/// projects, padding and all, because these bytes are hashed into the item version: a change here is a diff in
/// every user's repo, and a test written from imagination would not notice.</para>
/// </summary>
public class TaskDescriptorFormatTests
{
    // lenze-mid MainTask: a µs watchdog, a TIME-LITERAL interval (no unit to append), five calls.
    private const string LenzeMain =
        "Type:      Cyclic\n" +
        "Interval:  t#4ms\n" +
        "Priority:  1\n" +
        "Watchdog:  3200 µs (sensitivity 2)\n" +
        "Calls:     Simulation, General, Mach1_MotionControl, MachineStateSetting, FirstErrorCapture\n";

    // lenze-mid OEE_Task: a BARE-NUMBER interval, which is the arm that gets its unit appended.
    private const string LenzeOee =
        "Type:      Cyclic\n" +
        "Interval:  20 ms\n" +
        "Priority:  5\n" +
        "Watchdog:  16 ms (sensitivity 2)\n" +
        "Calls:     ProductionDataInputs\n";

    [Theory]
    [InlineData(LenzeMain)]
    [InlineData(LenzeOee)]
    // A task with no watchdog spells it `off` rather than omitting the line.
    [InlineData("Type:      Cyclic\nInterval:  20 ms\nPriority:  5\nWatchdog:  off\n")]
    // …and one that drives nothing omits `Calls` ENTIRELY: an empty `Calls:` would read as an unnamed callee.
    [InlineData("Type:      Freewheeling\nPriority:  8\nWatchdog:  off\n")]
    // An event task carries the triggering variable.
    [InlineData("Type:      Event\nPriority:  3\nEvent:     GVL.Trigger\nWatchdog:  off\n")]
    public void A_real_task_file_is_a_fixed_point(string body) =>
        Assert.Equal(body, TaskDescriptorFormat.Write(TaskDescriptorFormat.Read(body)));

    [Fact]
    public void The_parts_are_read_back_as_parts_not_as_one_string()
    {
        var t = TaskDescriptorFormat.Read(LenzeMain);
        Assert.Equal("Cyclic", t.Type);
        Assert.Equal("1", t.Priority);
        // A TIME literal keeps its letters and gains NO unit — `Unitize` only joins a bare number, so splitting
        // `t#4ms` into a value and a unit would invent one and then render it back doubled.
        Assert.Equal("t#4ms", t.Interval);
        Assert.Equal("", t.IntervalUnit);
        Assert.Equal("3200", t.Watchdog!.Time);
        Assert.Equal("µs", t.Watchdog!.Unit);
        Assert.Equal("2", t.Watchdog!.Sensitivity);
        Assert.Equal(new[] { "Simulation", "General", "Mach1_MotionControl", "MachineStateSetting", "FirstErrorCapture" },
                     t.Calls);
    }

    [Fact]
    public void A_bare_number_interval_keeps_its_unit_apart()
    {
        var t = TaskDescriptorFormat.Read(LenzeOee);
        Assert.Equal("20", t.Interval);
        Assert.Equal("ms", t.IntervalUnit);
    }

    [Fact]
    public void An_off_watchdog_is_absent_rather_than_zeroed()
    {
        // The vendor keeps stale numbers behind a disabled flag; `null` is how this model says "off" so those
        // numbers can never be written back as if they were live.
        Assert.Null(TaskDescriptorFormat.Read("Type:      Cyclic\nPriority:  5\nWatchdog:  off\n").Watchdog);
    }

    [Fact]
    public void A_FIELD_VOLT_DOES_NOT_KNOW_IS_REFUSED_not_dropped()
    {
        // The failure that matters: a push must never silently discard something the engineer wrote. A field
        // this format cannot round-trip is a field the next pull would delete.
        var ex = Assert.Throws<TaskDescriptorException>(() =>
            TaskDescriptorFormat.Read("Type:      Cyclic\nPriority:  5\nCoreBinding: 2\n"));
        Assert.Contains("CoreBinding", ex.Message);
    }

    [Theory]
    [InlineData("Priority:  5\n", "Type")]                                   // no kind
    [InlineData("Type:      Cyclic\n", "Priority")]                          // no priority
    public void The_fields_a_task_cannot_do_without_are_required(string body, string missing)
    {
        Assert.Contains(missing, Assert.Throws<TaskDescriptorException>(() => TaskDescriptorFormat.Read(body)).Message);
    }

    [Fact]
    public void A_malformed_watchdog_says_what_it_expected()
    {
        var ex = Assert.Throws<TaskDescriptorException>(() =>
            TaskDescriptorFormat.Read("Type:      Cyclic\nPriority:  5\nWatchdog:  3200 µs\n"));
        Assert.Contains("sensitivity", ex.Message);
    }

    [Fact]
    public void The_gate_refuses_a_non_canonical_body_and_prints_the_one_to_use()
    {
        // Hand-typed spacing parses fine and would be REWRITTEN by the next pull. Refusing it with the exact
        // canonical text is the same bargain NetworkTextGate strikes for graphical bodies.
        var ex = Assert.Throws<TaskDescriptorException>(() =>
            TaskDescriptorFormat.Gate("Type: Cyclic\nPriority: 5\nWatchdog: off\n"));
        Assert.Contains("Type:      Cyclic", ex.Message);
    }

    [Fact]
    public void The_gate_accepts_what_a_pull_actually_wrote()
    {
        Assert.Equal("1", TaskDescriptorFormat.Gate(LenzeMain).Priority);
        // …and tolerates a lost trailing newline, which an editor can do on its own and is not drift worth refusing.
        Assert.Equal("5", TaskDescriptorFormat.Gate(LenzeOee.TrimEnd('\n')).Priority);
    }

    [Fact]
    public void Calls_survive_order_and_spacing()
    {
        var t = TaskDescriptorFormat.Read("Type:      Cyclic\nPriority:  1\nWatchdog:  off\nCalls:     A,  B ,C\n");
        Assert.Equal(new[] { "A", "B", "C" }, t.Calls);
        // Order is the CALL ORDER — the sequence the task runs them in, so it is content, not a set.
        Assert.Equal("Calls:     A, B, C\n",
                     TaskDescriptorFormat.Write(t with { Type = "Cyclic" }).Split(new[] { "Watchdog:  off\n" }, System.StringSplitOptions.None)[1]);
    }

    [Fact]
    public void Settings_edited_in_the_workspace_render_back()
    {
        // What a user actually does: change the interval and add a POU to the call list.
        var t = TaskDescriptorFormat.Read(LenzeOee);
        var edited = t with { Interval = "50", Calls = new List<string>(t.Calls) { "NewPou" } };
        Assert.Equal(
            "Type:      Cyclic\nInterval:  50 ms\nPriority:  5\nWatchdog:  16 ms (sensitivity 2)\n" +
            "Calls:     ProductionDataInputs, NewPou\n",
            TaskDescriptorFormat.Write(edited));
    }
}
