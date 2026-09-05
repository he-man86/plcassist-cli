using System;
using System.Collections.Generic;
using System.Linq;
using Volt.Contracts;
using Volt.Engine;
using Volt.Engine.Format.Task;
using Volt.Engine.Item;

namespace Volt.Ide.Twincat;

/// <summary>
/// A task's schedule and call list, over COM. The translation itself is <see cref="TcTaskSchedule"/> (pure, and
/// tested offline); what lives here is the pair of tree items a `.task` file is assembled from — the PLC task
/// node the caller hands in, and the SYSTEM task its <c>LinkedTask</c> names.
///
/// <para><b>Every write is READ BACK.</b> TwinCAT accepts <c>ConsumeXml</c> for fields it has no intention of
/// changing and reports nothing, and its tree items go stale after a mutation. A push that returns success over
/// an unchanged schedule is the one outcome worth failing for: the engineer's file would then claim a cycle time
/// the machine does not run, and the next pull would rewrite the file back without explaining why. So the write
/// re-reads and compares, and throws when the vendor did not take it.</para>
/// </summary>
internal sealed partial class TcObjectModel
{
    /// <summary>A PLC task's settings, assembled from the linked system task plus this item's call children.</summary>
    public TaskSettings ReadTask(object node) =>
        TcTaskSchedule.Read(ProduceXml(LinkedSystemTask(node)), CallNames(node));

    /// <summary>Apply a task's settings: the schedule onto the system task, the call list onto this item.
    /// Throws rather than half-apply — a task running the right POUs on the wrong cycle is not a partial
    /// success.</summary>
    public void WriteTask(object node, TaskSettings t)
    {
        var patch = TcTaskSchedule.SysTaskPatch(t);   // refuses what TwinCAT cannot express, before touching COM
        var path = LinkedTaskPath(node);

        ((dynamic)LookupTreeItem(path)).ConsumeXml(patch);

        // Re-LOOKUP rather than reuse the handle: a tree item is invalidated by a mutation ("Item 'x' is deleted
        // or invalidated by an ealier operation!"), which is the same trap `ReadManifest` records for the walk.
        if (!TcTaskSchedule.Matches(ProduceXml(LookupTreeItem(path)), t))
            throw new BridgeException(BridgeErrorCodes.Unsupported,
                $"TwinCAT accepted the schedule for '{GetName(node)}' and did not apply it — the system task " +
                $"'{path}' still reports a different priority or cycle time. Set it in the IDE; pushing it again " +
                "will not help.");

        WriteCallList(node, t.Calls);
    }

    /// <summary>The POUs this task calls, in call order. They are the task item's own children, one per POU.</summary>
    private List<string> CallNames(object node)
    {
        var names = new List<string>();
        var n = ChildCount(node);
        for (var i = 1; i <= n; i++)
        {
            var child = ChildAt(node, i);
            if (ItemType(child) == ItemKind.PlcProgRef) names.Add(GetName(child));
        }
        return names;
    }

    /// <summary>Make the task's children exactly the POUs named, in order.
    ///
    /// <para>Rebuilt rather than diffed, which is what the CODESYS twin does and for the same reason: the
    /// `Calls:` line means "these POUs, in this order", and order is a property of the whole list. The no-change
    /// case returns early — re-creating identical children would churn the project file on every push of an
    /// unrelated field.</para></summary>
    private void WriteCallList(object node, IReadOnlyList<string> calls)
    {
        var current = CallNames(node);
        if (current.SequenceEqual(calls, StringComparer.Ordinal)) return;

        foreach (var name in current) DeleteChild(node, name);
        foreach (var name in calls) CreateChild(node, name, ItemKind.PlcProgRef);

        var after = CallNames(node);
        if (!after.SequenceEqual(calls, StringComparer.Ordinal))
            throw new BridgeException(BridgeErrorCodes.Unsupported,
                $"TwinCAT did not take the call list for '{GetName(node)}': asked for " +
                $"[{string.Join(", ", calls)}], the task now calls [{string.Join(", ", after)}]. " +
                "A POU can only be called by a task that can see it — check the name.");
    }

    /// <summary>The system task a PLC task points at. NOT optional: a PLC task with no <c>LinkedTask</c> has no
    /// schedule anywhere, and answering with a default would invent one.</summary>
    private string LinkedTaskPath(object node) =>
        TcTaskSchedule.LinkedTaskPath(ProduceXml(node))
        ?? throw new BridgeException(BridgeErrorCodes.Unsupported,
            $"TwinCAT: task '{GetName(node)}' names no linked system task, so it has no schedule to read or " +
            "write. This is a task the IDE itself would show as unconfigured.");

    private object LinkedSystemTask(object node) => LookupTreeItem(LinkedTaskPath(node));
}
