using System.Text.Json.Serialization;

namespace ZhanGuo.Core.Model;

/// <summary>整局状态。这是权威数据，不含任何显示信息。</summary>
public sealed class GameState
{
    public int Version { get; set; } = 1;
    public int Turn { get; set; }
    public int Year { get; set; } = -1;
    public int Season { get; set; }
    public List<Nation> Nations { get; set; } = new();

    public Nation? Find(string id) => Nations.FirstOrDefault(n => n.Id == id);
}

public sealed class Nation
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";

    /// <summary>预备兵力</summary>
    public double Reserve { get; set; }

    /// <summary>行政建设（行政开支的分母，0.3–1.2）</summary>
    public double AdminLevel { get; set; }

    /// <summary>军治清明（军事开支的除数）</summary>
    public double MilitaryDiscipline { get; set; }

    /// <summary>官僚腐化（总税收的折扣）</summary>
    public double Corruption { get; set; }

    /// <summary>国库存量</summary>
    public double Treasury { get; set; }

    public PopulationWeights Weights { get; set; } = new();

    public List<PopulationGroup> PopulationGroups { get; set; } = new();
    public List<TaxItem> Taxes { get; set; } = new();
    public List<ExpenseItem> Expenses { get; set; } = new();
    public List<Army> Armies { get; set; } = new();
    public List<Institution> Institutions { get; set; } = new();
    public List<Situation> Situations { get; set; } = new();

    public PopulationGroup? Group(string id) => PopulationGroups.FirstOrDefault(g => g.Id == id);
}

/// <summary>都/城/邑 的人口权重（原表 P/Q/R 列，全局常数）</summary>
public sealed class PopulationWeights
{
    public double Du { get; set; } = 120;
    public double Cheng { get; set; } = 60;
    public double Yi { get; set; } = 30;
}

public sealed class PopulationGroup
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";

    public double Du { get; set; }
    public double Cheng { get; set; }
    public double Yi { get; set; }
    public double Wild { get; set; }

    /// <summary>找补（人工配平项）</summary>
    public double Adjustment { get; set; }

    /// <summary>该行“都”的人口权重（原表 P 列，逐行不同）</summary>
    public double WeightDu { get; set; } = 120;

    /// <summary>该行“城”的人口权重（原表 Q 列）</summary>
    public double WeightCheng { get; set; } = 60;

    /// <summary>该行“邑”的人口权重（原表 R 列；魏国就有 30/25/20 三种）</summary>
    public double WeightYi { get; set; } = 30;

    /// <summary>产业开发 0–1</summary>
    public double Development { get; set; }

    /// <summary>户口建设 0–1</summary>
    public double Household { get; set; }

    /// <summary>产业基数</summary>
    public double Base { get; set; }

    public string? CoreCity { get; set; }
    public string? PopType { get; set; }
    public string? Note { get; set; }
}

public sealed class TaxItem
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";

    /// <summary>税基文案（如“传统鲁地”），仅用于显示</summary>
    public string? BaseLabel { get; set; }

    /// <summary>该税种覆盖的人群 id —— 取代原表的写死行区间</summary>
    public List<string> GroupIds { get; set; } = new();

    /// <summary>税额</summary>
    public double Amount { get; set; }

    /// <summary>效率 0–1</summary>
    public double Efficiency { get; set; }
}

public enum ExpenseKind
{
    /// <summary>工程开支（负值）</summary>
    Project,
    /// <summary>判定修正（正负皆可）</summary>
    Modifier
}

public sealed class ExpenseItem
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public ExpenseKind Kind { get; set; }
    public double Amount { get; set; }

    /// <summary>判定修正的来源说明（原表没有，这是新增字段）</summary>
    public string? Memo { get; set; }
}

public sealed class Army
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";

    public double Infantry { get; set; }
    public double Elite { get; set; }
    public double Cavalry { get; set; }
    public double Chariots { get; set; }

    /// <summary>训练度（百分数，如 40 表示 40%）</summary>
    public double Training { get; set; }

    public string? Station { get; set; }
    public string? Commander { get; set; }
    public string? Note { get; set; }

    /// <summary>战备等级</summary>
    public double Readiness { get; set; }

    /// <summary>补给等级</summary>
    public double Supply { get; set; }

    // 单位维护成本系数。逐部队可配，因为原表里同兵种也可能逐国不同
    // （例：越国水师 250，别国 300）。
    public double CostInfantry { get; set; } = 60;
    public double CostElite { get; set; } = 150;
    public double CostCavalry { get; set; } = 180;
    public double CostChariots { get; set; } = 300;

    /// <summary>原始维护费公式，仅用于审计对照</summary>
    public string? UpkeepFormula { get; set; }

    [JsonIgnore]
    public bool IsBuilt => !string.Equals(Note, "未建设", StringComparison.Ordinal);
}

public sealed class Institution
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";

    /// <summary>该等级对应的描述文本（原表“我国情况”）</summary>
    public string? Description { get; set; }

    /// <summary>I–IV → 1–4</summary>
    public int Level { get; set; } = 1;

    public string? ReformPoint { get; set; }
}

public sealed class Situation
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string? Description { get; set; }
}
