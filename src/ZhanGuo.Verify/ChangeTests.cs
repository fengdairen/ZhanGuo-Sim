using ZhanGuo.Core.Changes;
using ZhanGuo.Core.Model;
using ZhanGuo.Core.Rules;
using ZhanGuo.Core.Serialization;

namespace ZhanGuo.Verify;

/// <summary>变更单的行为测试：加减、跨地转移、校验拒绝、预览不改状态。</summary>
public static class ChangeTests
{
    private static int _pass;
    private static int _fail;
    private static readonly List<string> Log = new();

    private static void Check(string name, bool ok, string detail = "")
    {
        if (ok) { _pass++; Log.Add($"  [通过] {name}"); }
        else { _fail++; Log.Add($"  [失败] {name}  {detail}"); }
    }

    private static bool Near(double a, double b, double tol = 1e-9) => Math.Abs(a - b) <= tol;

    public static int Run(string root)
    {
        var path = Path.Combine(root, "data", "state.json");
        var state = StateLoader.Load(path);

        // ---------- 1. 加减 ----------
        var wei = state.Find("wei")!;
        var group = wei.PopulationGroups.First(); // 中山人
        var yiBefore = group.Yi;
        var popBefore = Economy.Population(wei);

        var cs1 = new ChangeSet();
        cs1.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Adjust,
            Target = new DataRef(EntityKind.Group, "wei", group.Id),
            Field = FieldId.Yi,
            Value = 3,
            Memo = "测试：加三邑",
        });
        var h0 = ChangeSet.Hash(state);
        var count1 = cs1.Commit(state, out var err1);
        Check("加减：提交成功", count1 == 1, err1 ?? "");

        wei = state.Find("wei")!;
        group = wei.PopulationGroups.First();
        Check("加减：邑 +3", Near(group.Yi, yiBefore + 3), $"实际 {group.Yi}");
        Check("加减：人口按邑权重增长", Near(Economy.Population(wei), popBefore + 3 * group.WeightYi),
            $"实际 {Economy.Population(wei)}，期望 {popBefore + 3 * group.WeightYi}");
        Check("加减：状态哈希已变", ChangeSet.Hash(state) != h0);

        // ---------- 2. 跨地转移（新建目标人群） ----------
        var weiGroup = state.Find("wei")!.PopulationGroups.First();
        var chu = state.Find("chu")!;
        var chuGroupCount = chu.PopulationGroups.Count;
        var yiBefore2 = weiGroup.Yi;
        var popWeiBefore = Economy.Population(state.Find("wei")!);
        var popChuBefore = Economy.Population(chu);

        var cs2 = new ChangeSet();
        cs2.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Transfer,
            Target = new DataRef(EntityKind.Group, "wei", weiGroup.Id),
            Field = FieldId.Yi,
            Value = 3,
            To = new DataRef(EntityKind.Group, "chu", "gTestTransfer"),
            CreateIfMissing = true,
            Memo = "测试：割三邑入楚",
        });
        var count2 = cs2.Commit(state, out var err2);
        Check("转移：提交成功", count2 == 1, err2 ?? "");

        weiGroup = state.Find("wei")!.PopulationGroups.First();
        chu = state.Find("chu")!;
        var newGroup = chu.Group("gTestTransfer");
        Check("转移：来源邑 -3", Near(weiGroup.Yi, yiBefore2 - 3), $"实际 {weiGroup.Yi}");
        Check("转移：目标人群已新建", newGroup is not null);
        Check("转移：目标邑 = 3", newGroup is not null && Near(newGroup.Yi, 3), $"实际 {newGroup?.Yi}");
        Check("转移：楚国人群数 +1", chu.PopulationGroups.Count == chuGroupCount + 1);
        var popWeiAfter = Economy.Population(state.Find("wei")!);
        var popChuAfter = Economy.Population(chu);
        Check("转移：魏国人口减少 3×邑权重",
            Near(popWeiAfter, popWeiBefore - 3 * weiGroup.WeightYi),
            $"实际 {popWeiAfter}，期望 {popWeiBefore - 3 * weiGroup.WeightYi}");
        Check("转移：楚国人口增加 3×邑权重",
            Near(popChuAfter, popChuBefore + 3 * weiGroup.WeightYi),
            $"实际 {popChuAfter}，期望 {popChuBefore + 3 * weiGroup.WeightYi}");
        Check("转移：两国人口总量守恒",
            Near(popWeiAfter + popChuAfter, popWeiBefore + popChuBefore),
            $"实际 {popWeiAfter + popChuAfter}，期望 {popWeiBefore + popChuBefore}");

        // ---------- 3. 拒绝 ----------
        var cs3 = new ChangeSet();
        cs3.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Transfer,
            Target = new DataRef(EntityKind.Group, "wei", state.Find("wei")!.PopulationGroups.First().Id),
            Field = FieldId.Yi,
            Value = 9999,
            To = new DataRef(EntityKind.Group, "chu", "gTestTransfer"),
            Memo = "测试：转出超额",
        });
        var bad3 = cs3.Commit(state, out var err3);
        Check("拒绝：转出超过存量", bad3 < 0 && err3 is not null, err3 ?? "(未报错)");

        var cs4 = new ChangeSet();
        cs4.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Adjust,
            Target = new DataRef(EntityKind.Group, "wei", state.Find("wei")!.PopulationGroups.First().Id),
            Field = FieldId.Yi,
            Value = -9999,
            Memo = "测试：减成负数",
        });
        var bad4 = cs4.Commit(state, out var err4);
        Check("拒绝：减成负数", bad4 < 0 && err4 is not null, err4 ?? "(未报错)");

        var cs5 = new ChangeSet();
        cs5.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Adjust,
            Target = new DataRef(EntityKind.Nation, "wei", null),
            Field = FieldId.Treasury,
            Value = 10,
            Memo = "",
        });
        var bad5 = cs5.Commit(state, out _);
        Check("拒绝：空事由", bad5 < 0);

        var cs6 = new ChangeSet();
        cs6.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Transfer,
            Target = new DataRef(EntityKind.Nation, "wei", null),
            Field = FieldId.Treasury,
            Value = 10,
            To = new DataRef(EntityKind.Nation, "chu", null),
            Memo = "测试：转移连续量",
        });
        var bad6 = cs6.Commit(state, out var err6);
        Check("拒绝：转移非离散量", bad6 < 0 && err6 is not null, err6 ?? "(未报错)");

        // ---------- 4. 原子性：一批里有一条失败，整批不落地 ----------
        var yiNow = state.Find("wei")!.PopulationGroups.First().Yi;
        var cs7 = new ChangeSet();
        cs7.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Adjust,
            Target = new DataRef(EntityKind.Group, "wei", state.Find("wei")!.PopulationGroups.First().Id),
            Field = FieldId.Yi, Value = 1, Memo = "前半条：合法"
        });
        cs7.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Adjust,
            Target = new DataRef(EntityKind.Group, "wei", state.Find("wei")!.PopulationGroups.First().Id),
            Field = FieldId.Yi, Value = -9999, Memo = "后半条：非法"
        });
        var bad7 = cs7.Commit(state, out _);
        var yiAfter7 = state.Find("wei")!.PopulationGroups.First().Yi;
        Check("原子性：整批失败", bad7 < 0);
        Check("原子性：失败的批次不改变任何数据", Near(yiAfter7, yiNow), $"实际 {yiAfter7}，期望 {yiNow}");

        // ---------- 5. 预览不修改状态 ----------
        var hBefore = ChangeSet.Hash(state);
        var cs8 = new ChangeSet();
        cs8.Ops.Add(new ChangeOp
        {
            Kind = OpKind.Adjust,
            Target = new DataRef(EntityKind.Group, "wei", state.Find("wei")!.PopulationGroups.First().Id),
            Field = FieldId.Yi, Value = 5, Memo = "测试：只预览"
        });
        var preview = cs8.Preview(state, out var err8);
        Check("预览：无错误", err8 is null && preview.Count > 0, err8 ?? "");
        Check("预览：不改变状态哈希", ChangeSet.Hash(state) == hBefore);

        // ---------- 输出 ----------
        Log.Insert(0, "=== 变更单行为测试 ===");
        Log.Add("");
        Log.Add($"通过 {_pass} 项，失败 {_fail} 项");
        var report = string.Join(Environment.NewLine, Log);
        Directory.CreateDirectory(Path.Combine(root, "tools"));
        File.WriteAllText(Path.Combine(root, "tools", "_changes_test.log"), report,
            new System.Text.UTF8Encoding(false));

        Console.WriteLine($"changes: pass={_pass} fail={_fail}");
        Console.WriteLine(_fail == 0 ? "PASS" : "FAIL");
        return _fail == 0 ? 0 : 1;
    }
}
