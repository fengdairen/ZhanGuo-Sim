using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ZhanGuo.Core.Model;
using ZhanGuo.Core.Serialization;

namespace ZhanGuo.Core.Changes;

/// <summary>可被变更单指向的实体种类。</summary>
public enum EntityKind
{
    Nation,
    Group,
    Tax,
    Expense,
    Army,
    Institution,
}

/// <summary>可被调整的字段。用枚举而不是字符串，避免写错字段名。</summary>
public enum FieldId
{
    // 国
    Reserve, AdminLevel, MilitaryDiscipline, Corruption, Treasury,
    // 人群
    Du, Cheng, Yi, Wild, Adjustment, Development, Household, Base, WeightYi,
    // 税目
    TaxAmount, TaxEfficiency,
    // 开支
    ExpenseAmount,
    // 军队
    Infantry, Elite, Cavalry, Chariots, Training, Readiness, Supply,
    // 制度
    InstitutionLevel,
}

public static class FieldMeta
{
    public sealed record Info(string Display, bool Discrete, double Min = double.NegativeInfinity, double Max = double.PositiveInfinity);

    public static readonly IReadOnlyDictionary<FieldId, Info> All = new Dictionary<FieldId, Info>
    {
        [FieldId.Reserve] = new("预备兵力", true, 0),
        [FieldId.AdminLevel] = new("行政建设", false, 0.05, 2),
        [FieldId.MilitaryDiscipline] = new("军治清明", false, 0, 1),
        [FieldId.Corruption] = new("官僚腐化", false, 0, 1),
        [FieldId.Treasury] = new("国库存量", false),

        [FieldId.Du] = new("都（座）", true, 0),
        [FieldId.Cheng] = new("城（座）", true, 0),
        [FieldId.Yi] = new("邑（座）", true, 0),
        [FieldId.Wild] = new("野地（块）", true, 0),
        [FieldId.Adjustment] = new("找补", true),
        [FieldId.Development] = new("产业开发", false, 0, 1),
        [FieldId.Household] = new("户口建设", false, 0, 1),
        [FieldId.Base] = new("产业基数", false, 0),
        [FieldId.WeightYi] = new("邑权重", false, 0),

        [FieldId.TaxAmount] = new("税额", false, 0),
        [FieldId.TaxEfficiency] = new("效率", false, 0, 1),

        [FieldId.ExpenseAmount] = new("金额", false),

        [FieldId.Infantry] = new("步卒", true, 0),
        [FieldId.Elite] = new("甲士", true, 0),
        [FieldId.Cavalry] = new("辅骑", true, 0),
        [FieldId.Chariots] = new("战车", true, 0),
        [FieldId.Training] = new("训练度", false, 0, 100),
        [FieldId.Readiness] = new("战备等级", false, 0),
        [FieldId.Supply] = new("补给等级", false, 0),

        [FieldId.InstitutionLevel] = new("制度等级", true, 1, 4),
    };

    /// <summary>某种实体可用的字段（供 UI 过滤）。</summary>
    public static IReadOnlyList<FieldId> For(EntityKind kind) => kind switch
    {
        EntityKind.Nation => new[] { FieldId.Reserve, FieldId.AdminLevel, FieldId.MilitaryDiscipline, FieldId.Corruption, FieldId.Treasury },
        EntityKind.Group => new[] { FieldId.Du, FieldId.Cheng, FieldId.Yi, FieldId.Wild, FieldId.Adjustment, FieldId.Development, FieldId.Household, FieldId.Base, FieldId.WeightYi },
        EntityKind.Tax => new[] { FieldId.TaxAmount, FieldId.TaxEfficiency },
        EntityKind.Expense => new[] { FieldId.ExpenseAmount },
        EntityKind.Army => new[] { FieldId.Infantry, FieldId.Elite, FieldId.Cavalry, FieldId.Chariots, FieldId.Training, FieldId.Readiness, FieldId.Supply },
        EntityKind.Institution => new[] { FieldId.InstitutionLevel },
        _ => Array.Empty<FieldId>(),
    };

    public static string DisplayOf(FieldId f) => All.TryGetValue(f, out var i) ? i.Display : f.ToString();
    public static bool IsDiscrete(FieldId f) => All.TryGetValue(f, out var i) && i.Discrete;
}

/// <summary>指向一个具体的数据位置。</summary>
public sealed record DataRef(EntityKind Kind, string? NationId, string? EntityId)
{
    public string Describe(GameState s)
    {
        if (Kind == EntityKind.Nation)
            return $"{s.Find(NationId ?? "")?.Name ?? NationId}国";
        var n = s.Find(NationId ?? "");
        var name = Kind switch
        {
            EntityKind.Group => n?.Group(EntityId ?? "")?.Name,
            EntityKind.Tax => n?.Taxes.FirstOrDefault(t => t.Id == EntityId)?.Name,
            EntityKind.Expense => n?.Expenses.FirstOrDefault(e => e.Id == EntityId)?.Name,
            EntityKind.Army => n?.Armies.FirstOrDefault(a => a.Id == EntityId)?.Name,
            EntityKind.Institution => n?.Institutions.FirstOrDefault(i => i.Id == EntityId)?.Name,
            _ => null
        } ?? EntityId;
        return $"{n?.Name}·{name}";
    }
}

public enum OpKind
{
    /// <summary>在现有值上加减（推荐）</summary>
    Adjust,
    /// <summary>直接设为某值（仅用于初始化或纠错，会记录为强改）</summary>
    Set,
    /// <summary>把某个离散量从 A 转移到 B（如“割三邑入楚”）</summary>
    Transfer,
}

/// <summary>一条数据变更。这是人和 LLM 共同使用的唯一写入格式。</summary>
public sealed class ChangeOp
{
    public OpKind Kind { get; set; }
    public DataRef Target { get; set; } = new(EntityKind.Nation, null, null);
    public FieldId Field { get; set; }
    public double Value { get; set; }

    /// <summary>Transfer 的目标；Target 是来源</summary>
    public DataRef? To { get; set; }

    /// <summary>事由。必填，这是审计的根。</summary>
    public string Memo { get; set; } = "";

    /// <summary>若 Transfer 的目标实体不存在，是否自动新建（仅人群支持）</summary>
    public bool CreateIfMissing { get; set; }

    public string Describe()
    {
        var sign = Value >= 0 ? "+" : "";
        var f = FieldMeta.DisplayOf(Field);
        return Kind switch
        {
            OpKind.Adjust => $"调整 {f} {sign}{Value:0.##}",
            OpKind.Set => $"设定 {f} = {Value:0.##}（强改）",
            OpKind.Transfer => $"转移 {f} {Value:0.##} → " + (To is null ? "?" : "…"),
            _ => "?"
        };
    }
}

/// <summary>字段读写。集中一处，避免各层各自实现。</summary>
public static class FieldAccess
{
    public static bool TryGet(GameState s, DataRef r, FieldId f, out double value)
    {
        value = 0;
        var n = s.Find(r.NationId ?? "");
        switch (r.Kind, f)
        {
            case (EntityKind.Nation, FieldId.Reserve) when n is not null: value = n.Reserve; return true;
            case (EntityKind.Nation, FieldId.AdminLevel) when n is not null: value = n.AdminLevel; return true;
            case (EntityKind.Nation, FieldId.MilitaryDiscipline) when n is not null: value = n.MilitaryDiscipline; return true;
            case (EntityKind.Nation, FieldId.Corruption) when n is not null: value = n.Corruption; return true;
            case (EntityKind.Nation, FieldId.Treasury) when n is not null: value = n.Treasury; return true;

            case (EntityKind.Group, FieldId.Du) when G() is { } g: value = g.Du; return true;
            case (EntityKind.Group, FieldId.Cheng) when G() is { } g: value = g.Cheng; return true;
            case (EntityKind.Group, FieldId.Yi) when G() is { } g: value = g.Yi; return true;
            case (EntityKind.Group, FieldId.Wild) when G() is { } g: value = g.Wild; return true;
            case (EntityKind.Group, FieldId.Adjustment) when G() is { } g: value = g.Adjustment; return true;
            case (EntityKind.Group, FieldId.Development) when G() is { } g: value = g.Development; return true;
            case (EntityKind.Group, FieldId.Household) when G() is { } g: value = g.Household; return true;
            case (EntityKind.Group, FieldId.Base) when G() is { } g: value = g.Base; return true;
            case (EntityKind.Group, FieldId.WeightYi) when G() is { } g: value = g.WeightYi; return true;

            case (EntityKind.Tax, FieldId.TaxAmount) when T() is { } t: value = t.Amount; return true;
            case (EntityKind.Tax, FieldId.TaxEfficiency) when T() is { } t: value = t.Efficiency; return true;

            case (EntityKind.Expense, FieldId.ExpenseAmount) when E() is { } e: value = e.Amount; return true;

            case (EntityKind.Army, FieldId.Infantry) when A() is { } a: value = a.Infantry; return true;
            case (EntityKind.Army, FieldId.Elite) when A() is { } a: value = a.Elite; return true;
            case (EntityKind.Army, FieldId.Cavalry) when A() is { } a: value = a.Cavalry; return true;
            case (EntityKind.Army, FieldId.Chariots) when A() is { } a: value = a.Chariots; return true;
            case (EntityKind.Army, FieldId.Training) when A() is { } a: value = a.Training; return true;
            case (EntityKind.Army, FieldId.Readiness) when A() is { } a: value = a.Readiness; return true;
            case (EntityKind.Army, FieldId.Supply) when A() is { } a: value = a.Supply; return true;

            case (EntityKind.Institution, FieldId.InstitutionLevel) when I() is { } i: value = i.Level; return true;
        }
        return false;

        PopulationGroup? G() => n?.Group(r.EntityId ?? "");
        TaxItem? T() => n?.Taxes.FirstOrDefault(x => x.Id == r.EntityId);
        ExpenseItem? E() => n?.Expenses.FirstOrDefault(x => x.Id == r.EntityId);
        Army? A() => n?.Armies.FirstOrDefault(x => x.Id == r.EntityId);
        Institution? I() => n?.Institutions.FirstOrDefault(x => x.Id == r.EntityId);
    }

    public static bool TrySet(GameState s, DataRef r, FieldId f, double value)
    {
        var n = s.Find(r.NationId ?? "");
        switch (r.Kind, f)
        {
            case (EntityKind.Nation, FieldId.Reserve) when n is not null: n.Reserve = value; return true;
            case (EntityKind.Nation, FieldId.AdminLevel) when n is not null: n.AdminLevel = value; return true;
            case (EntityKind.Nation, FieldId.MilitaryDiscipline) when n is not null: n.MilitaryDiscipline = value; return true;
            case (EntityKind.Nation, FieldId.Corruption) when n is not null: n.Corruption = value; return true;
            case (EntityKind.Nation, FieldId.Treasury) when n is not null: n.Treasury = value; return true;

            case (EntityKind.Group, FieldId.Du) when G() is { } g: g.Du = value; return true;
            case (EntityKind.Group, FieldId.Cheng) when G() is { } g: g.Cheng = value; return true;
            case (EntityKind.Group, FieldId.Yi) when G() is { } g: g.Yi = value; return true;
            case (EntityKind.Group, FieldId.Wild) when G() is { } g: g.Wild = value; return true;
            case (EntityKind.Group, FieldId.Adjustment) when G() is { } g: g.Adjustment = value; return true;
            case (EntityKind.Group, FieldId.Development) when G() is { } g: g.Development = value; return true;
            case (EntityKind.Group, FieldId.Household) when G() is { } g: g.Household = value; return true;
            case (EntityKind.Group, FieldId.Base) when G() is { } g: g.Base = value; return true;
            case (EntityKind.Group, FieldId.WeightYi) when G() is { } g: g.WeightYi = value; return true;

            case (EntityKind.Tax, FieldId.TaxAmount) when T() is { } t: t.Amount = value; return true;
            case (EntityKind.Tax, FieldId.TaxEfficiency) when T() is { } t: t.Efficiency = value; return true;

            case (EntityKind.Expense, FieldId.ExpenseAmount) when E() is { } e: e.Amount = value; return true;

            case (EntityKind.Army, FieldId.Infantry) when A() is { } a: a.Infantry = value; return true;
            case (EntityKind.Army, FieldId.Elite) when A() is { } a: a.Elite = value; return true;
            case (EntityKind.Army, FieldId.Cavalry) when A() is { } a: a.Cavalry = value; return true;
            case (EntityKind.Army, FieldId.Chariots) when A() is { } a: a.Chariots = value; return true;
            case (EntityKind.Army, FieldId.Training) when A() is { } a: a.Training = value; return true;
            case (EntityKind.Army, FieldId.Readiness) when A() is { } a: a.Readiness = value; return true;
            case (EntityKind.Army, FieldId.Supply) when A() is { } a: a.Supply = value; return true;

            case (EntityKind.Institution, FieldId.InstitutionLevel) when I() is { } i: i.Level = (int)Math.Round(value); return true;
        }
        return false;

        PopulationGroup? G() => n?.Group(r.EntityId ?? "");
        TaxItem? T() => n?.Taxes.FirstOrDefault(x => x.Id == r.EntityId);
        ExpenseItem? E() => n?.Expenses.FirstOrDefault(x => x.Id == r.EntityId);
        Army? A() => n?.Armies.FirstOrDefault(x => x.Id == r.EntityId);
        Institution? I() => n?.Institutions.FirstOrDefault(x => x.Id == r.EntityId);
    }
}

/// <summary>一条变更对某个位置造成的前后变化（供预览）。</summary>
public sealed record FieldDelta(string Where, string Field, double Before, double After)
{
    public string Text => $"{Where}  {Field}：{Before:0.##} → {After:0.##}（{(After - Before >= 0 ? "+" : "")}{After - Before:0.##}）";
}

/// <summary>一批变更。提交前可预览，提交时整体校验，任一失败则全部不落地。</summary>
public sealed class ChangeSet
{
    public List<ChangeOp> Ops { get; } = new();

    /// <summary>校验并预览；不会修改 state。</summary>
    public IReadOnlyList<FieldDelta> Preview(GameState state, out string? error)
    {
        error = null;
        var deltas = new List<FieldDelta>();
        // 在副本上试算，避免污染真实状态
        var clone = Clone(state);
        foreach (var op in Ops)
        {
            if (!ApplyOne(clone, op, deltas, out var err))
            {
                error = err;
                return Array.Empty<FieldDelta>();
            }
        }
        return deltas;
    }

    /// <summary>整体提交。全部成功才写入；返回写入的变更数。</summary>
    public int Commit(GameState state, out string? error)
    {
        error = null;
        var clone = Clone(state);
        var deltas = new List<FieldDelta>();
        foreach (var op in Ops)
        {
            if (!ApplyOne(clone, op, deltas, out error)) return -1;
        }
        // 通过：把副本的内容整体搬回原对象（保持引用不变）
        var json = JsonSerializer.Serialize(clone, StateLoader.Options);
        var fresh = JsonSerializer.Deserialize<GameState>(json, StateLoader.Options)!;
        state.Nations.Clear();
        state.Nations.AddRange(fresh.Nations);
        state.Turn = fresh.Turn;
        return Ops.Count;
    }

    private static GameState Clone(GameState s) =>
        JsonSerializer.Deserialize<GameState>(JsonSerializer.Serialize(s, StateLoader.Options), StateLoader.Options)!;

    private static bool ApplyOne(GameState s, ChangeOp op, List<FieldDelta> deltas, out string? error)
    {
        error = null;

        if (string.IsNullOrWhiteSpace(op.Memo))
        {
            error = "每条变更都必须写明事由。";
            return false;
        }

        if (!FieldMeta.All.TryGetValue(op.Field, out var meta))
        {
            error = $"未知字段 {op.Field}";
            return false;
        }

        if (!FieldAccess.TryGet(s, op.Target, op.Field, out var before))
        {
            error = $"找不到位置：{op.Target.Describe(s)} / {meta.Display}";
            return false;
        }

        var where = op.Target.Describe(s);

        switch (op.Kind)
        {
            case OpKind.Set:
            {
                var after = op.Value;
                if (after < meta.Min - 1e-9 || after > meta.Max + 1e-9)
                {
                    error = $"{where} {meta.Display} 设为 {after:0.##} 越界（允许 {meta.Min:0.##}–{meta.Max:0.##}）";
                    return false;
                }
                FieldAccess.TrySet(s, op.Target, op.Field, after);
                deltas.Add(new FieldDelta(where, meta.Display, before, after));
                return true;
            }

            case OpKind.Adjust:
            {
                var after = before + op.Value;
                if (after < meta.Min - 1e-9 || after > meta.Max + 1e-9)
                {
                    error = $"{where} {meta.Display} {before:0.##}{op.Value:+0.##;-0.##} = {after:0.##} 越界（允许 {meta.Min:0.##}–{meta.Max:0.##}）";
                    return false;
                }
                FieldAccess.TrySet(s, op.Target, op.Field, after);
                deltas.Add(new FieldDelta(where, meta.Display, before, after));
                return true;
            }

            case OpKind.Transfer:
            {
                if (op.To is null)
                {
                    error = "转移缺少目标。";
                    return false;
                }
                if (!meta.Discrete)
                {
                    error = $"{meta.Display} 不是离散量，无法转移（可改为调整两地数值）。";
                    return false;
                }
                if (op.Value <= 0)
                {
                    error = "转移数量必须为正数。";
                    return false;
                }
                if (before < op.Value - 1e-9)
                {
                    error = $"{where} 只有 {before:0.##}，不足以转出 {op.Value:0.##}。";
                    return false;
                }

                var to = op.To;
                if (!FieldAccess.TryGet(s, to, op.Field, out var toBefore))
                {
                    // 人群目标可自动新建
                    if (op.CreateIfMissing && to.Kind == EntityKind.Group && to.EntityId is not null)
                    {
                        var srcNation = s.Find(op.Target.NationId ?? "");
                        var srcGroup = srcNation?.Group(op.Target.EntityId ?? "");
                        var dstNation = s.Find(to.NationId ?? "");
                        if (srcGroup is null || dstNation is null)
                        {
                            error = "自动新建人群失败：找不到源人群或目标国。";
                            return false;
                        }
                        var newGroup = new PopulationGroup
                        {
                            Id = to.EntityId,
                            Name = srcGroup.Name + "（新附）",
                            Development = srcGroup.Development,
                            Household = srcGroup.Household,
                            Base = srcGroup.Base,
                            WeightDu = srcGroup.WeightDu,
                            WeightCheng = srcGroup.WeightCheng,
                            WeightYi = srcGroup.WeightYi,
                            CoreCity = srcGroup.CoreCity,
                            PopType = srcGroup.PopType,
                            Note = op.Memo,
                        };
                        dstNation.PopulationGroups.Add(newGroup);
                        toBefore = 0;
                    }
                    else
                    {
                        error = $"转移目标不存在：{to.Describe(s)}";
                        return false;
                    }
                }

                FieldAccess.TrySet(s, op.Target, op.Field, before - op.Value);
                FieldAccess.TrySet(s, to, op.Field, toBefore + op.Value);
                deltas.Add(new FieldDelta(where, meta.Display, before, before - op.Value));
                deltas.Add(new FieldDelta(to.Describe(s), meta.Display, toBefore, toBefore + op.Value));
                return true;
            }
        }

        error = "未知操作类型。";
        return false;
    }

    public static string Hash(GameState s)
    {
        var json = JsonSerializer.Serialize(s, StateLoader.Options);
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json)))[..16];
    }
}
