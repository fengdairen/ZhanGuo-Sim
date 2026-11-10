namespace ZhanGuo.Core.Rules;

using ZhanGuo.Core.Model;

/// <summary>
/// 经济表的全部公式。纯函数、无状态、无副作用。
/// 每一个方法都对应原 Excel 里的一条公式（见注释），以便逐条校验。
/// </summary>
public static class Economy
{
    /// <summary>人群人口：= 都×P + 城×Q + 邑×R + 野地 + 找补（权重逐行不同）</summary>
    public static double Population(Nation n, PopulationGroup g) =>
        g.Du * g.WeightDu + g.Cheng * g.WeightCheng + g.Yi * g.WeightYi + g.Wild + g.Adjustment;

    /// <summary>国家总人口：= SUM(各人群人口)</summary>
    public static double Population(Nation n) =>
        n.PopulationGroups.Sum(g => Population(n, g));

    /// <summary>人群产值：= 人口 × 产业开发 × 产业基数 × √户口建设</summary>
    public static double Output(Nation n, PopulationGroup g) =>
        Population(n, g) * g.Development * g.Base * Math.Sqrt(g.Household);

    /// <summary>税基：= 该税种覆盖人群的产值之和（原表是写死的行区间，这里改为按 id 归组）</summary>
    public static double TaxBase(Nation n, TaxItem t) =>
        t.GroupIds.Sum(id => n.Group(id) is { } g ? Output(n, g) : 0);

    /// <summary>上税：= 税额 × 效率</summary>
    public static double TaxPaid(TaxItem t) => t.Amount * t.Efficiency;

    /// <summary>总税收：= SUM(上税) × √(1 − 官僚腐化)</summary>
    public static double TotalTax(Nation n) =>
        n.Taxes.Sum(TaxPaid) * Math.Sqrt(Math.Max(0, 1 - n.Corruption));

    /// <summary>
    /// 军队维护费：= (步×c1 + 甲×c2 + 辅骑×c3 + 车×c4) × √(1+训练/100) × √战备 × 补给
    /// 单位成本来自部队自身字段（原表中不同兵种、不同国家都可能不同）。
    /// </summary>
    public static double Upkeep(Army a) =>
        (a.Infantry * a.CostInfantry + a.Elite * a.CostElite
         + a.Cavalry * a.CostCavalry + a.Chariots * a.CostChariots)
        * Math.Sqrt(1 + a.Training / 100.0)
        * Math.Sqrt(Math.Max(0, a.Readiness))
        * a.Supply;

    /// <summary>军事开支：= SUM(维护费) ÷ √(1 + 军治清明)</summary>
    public static double MilitaryExpense(Nation n) =>
        n.Armies.Sum(Upkeep) / Math.Sqrt(1 + n.MilitaryDiscipline);

    /// <summary>行政开支：= (都×12 + 城×10 + 邑×6 + 人口×0.8) ÷ 行政建设^0.6</summary>
    public static double AdminExpense(Nation n)
    {
        var du = n.PopulationGroups.Sum(g => g.Du);
        var cheng = n.PopulationGroups.Sum(g => g.Cheng);
        var yi = n.PopulationGroups.Sum(g => g.Yi);
        var pop = Population(n);
        return (du * 12 + cheng * 10 + yi * 6 + pop * 0.8) / Math.Pow(Math.Max(1e-9, n.AdminLevel), 0.6);
    }

    /// <summary>工程开支合计（负值）</summary>
    public static double ProjectExpense(Nation n) =>
        n.Expenses.Where(e => e.Kind == ExpenseKind.Project).Sum(e => e.Amount);

    /// <summary>判定修正合计</summary>
    public static double ModifierTotal(Nation n) =>
        n.Expenses.Where(e => e.Kind == ExpenseKind.Modifier).Sum(e => e.Amount);

    /// <summary>总结余：= 工程开支 + 判定修正 + 总税收 − 军事开支 − 行政开支</summary>
    public static double Balance(Nation n) =>
        ProjectExpense(n) + ModifierTotal(n) + TotalTax(n) - MilitaryExpense(n) - AdminExpense(n);

    /// <summary>把一国的关键指标一次算齐，供 UI 与校验使用。</summary>
    public static NationTotals Totals(Nation n) => new(
        Population: Population(n),
        TotalTax: TotalTax(n),
        MilitaryExpense: MilitaryExpense(n),
        AdminExpense: AdminExpense(n),
        ProjectExpense: ProjectExpense(n),
        ModifierTotal: ModifierTotal(n),
        Balance: Balance(n),
        Treasury: n.Treasury);
}

public readonly record struct NationTotals(
    double Population,
    double TotalTax,
    double MilitaryExpense,
    double AdminExpense,
    double ProjectExpense,
    double ModifierTotal,
    double Balance,
    double Treasury);
