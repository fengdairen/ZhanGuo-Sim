using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using ZhanGuo.Core.Model;
using ZhanGuo.Core.Rules;

namespace ZhanGuo.Workbench.ViewModels;

/// <summary>
/// 行对象基类：把“编辑 → 写回模型 → 触发重算”封装掉。
/// UI 只认识这些行对象，不认识模型；模型也不认识 UI。
/// </summary>
public abstract class RowBase : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>任一字段被编辑后触发，由窗口订阅以重算</summary>
    public Action? Edited { get; set; }

    protected bool Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        OnEdited();
        return true;
    }

    protected void Raise(string name) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

    protected virtual void OnEdited() => Edited?.Invoke();

    /// <summary>重算本行依赖的派生值</summary>
    public virtual void Recalculate(Nation n) { }
}

public sealed class GroupRow : RowBase
{
    private readonly PopulationGroup _g;
    private readonly Nation _n;

    public GroupRow(Nation n, PopulationGroup g) { _n = n; _g = g; }

    public string Name => _g.Name;
    public string? CoreCity => _g.CoreCity;
    public string? PopType => _g.PopType;

    public double Du { get => _g.Du; set { _g.Du = value; Set(ref _du, value); } }
    private double _du;
    public double Cheng { get => _g.Cheng; set { _g.Cheng = value; Set(ref _cheng, value); } }
    private double _cheng;
    public double Yi { get => _g.Yi; set { _g.Yi = value; Set(ref _yi, value); } }
    private double _yi;
    public double Wild { get => _g.Wild; set { _g.Wild = value; Set(ref _wild, value); } }
    private double _wild;
    public double Adjustment { get => _g.Adjustment; set { _g.Adjustment = value; Set(ref _adj, value); } }
    private double _adj;
    public double Development { get => _g.Development; set { _g.Development = value; Set(ref _dev, value); } }
    private double _dev;
    public double Household { get => _g.Household; set { _g.Household = value; Set(ref _hh, value); } }
    private double _hh;
    public double Base { get => _g.Base; set { _g.Base = value; Set(ref _base, value); } }
    private double _base;
    public double WeightYi { get => _g.WeightYi; set { _g.WeightYi = value; Set(ref _wy, value); } }
    private double _wy;

    public double Population { get; private set; }
    public double Output { get; private set; }

    public override void Recalculate(Nation n)
    {
        Population = Economy.Population(n, _g);
        Output = Economy.Output(n, _g);
        Raise(nameof(Population));
        Raise(nameof(Output));
    }
}

public sealed class TaxRow : RowBase
{
    private readonly TaxItem _t;
    public TaxRow(TaxItem t) => _t = t;

    public string Name => _t.Name;
    public string? BaseLabel => _t.BaseLabel;
    public string Groups => string.Join("、", _t.GroupIds);

    public double Amount { get => _t.Amount; set { _t.Amount = value; Set(ref _amt, value); } }
    private double _amt;
    public double Efficiency { get => _t.Efficiency; set { _t.Efficiency = value; Set(ref _eff, value); } }
    private double _eff;

    public double TaxBase { get; private set; }
    public double Paid { get; private set; }

    public override void Recalculate(Nation n)
    {
        TaxBase = Economy.TaxBase(n, _t);
        Paid = Economy.TaxPaid(_t);
        Raise(nameof(TaxBase));
        Raise(nameof(Paid));
    }
}

public sealed class ExpenseRow : RowBase
{
    private readonly ExpenseItem _e;
    public ExpenseRow(ExpenseItem e) => _e = e;

    public string Name => _e.Name;
    public string Kind => _e.Kind == ExpenseKind.Project ? "工程" : "修正";

    public double Amount
    {
        get => _e.Amount;
        set { _e.Amount = value; Set(ref _amt, value); }
    }
    private double _amt;

    public string? Memo
    {
        get => _e.Memo;
        set { _e.Memo = value; Set(ref _memo, value); }
    }
    private string? _memo;
}

public sealed class ArmyRow : RowBase
{
    private readonly Army _a;
    public ArmyRow(Army a) => _a = a;

    public string Name => _a.Name;
    public string? Station => _a.Station;
    public string? Commander => _a.Commander;
    public string? Note => _a.Note;
    public bool IsBuilt => _a.IsBuilt;

    public double Infantry { get => _a.Infantry; set { _a.Infantry = value; Set(ref _inf, value); } }
    private double _inf;
    public double Elite { get => _a.Elite; set { _a.Elite = value; Set(ref _el, value); } }
    private double _el;
    public double Cavalry { get => _a.Cavalry; set { _a.Cavalry = value; Set(ref _cv, value); } }
    private double _cv;
    public double Chariots { get => _a.Chariots; set { _a.Chariots = value; Set(ref _ch, value); } }
    private double _ch;
    public double Training { get => _a.Training; set { _a.Training = value; Set(ref _tr, value); } }
    private double _tr;
    public double Readiness { get => _a.Readiness; set { _a.Readiness = value; Set(ref _rd, value); } }
    private double _rd;
    public double Supply { get => _a.Supply; set { _a.Supply = value; Set(ref _sp, value); } }
    private double _sp;

    public double Upkeep { get; private set; }

    public override void Recalculate(Nation n)
    {
        Upkeep = Economy.Upkeep(_a);
        Raise(nameof(Upkeep));
    }
}

public sealed class InstitutionRow : RowBase
{
    private readonly Institution _i;
    public InstitutionRow(Institution i) => _i = i;

    public string Name => _i.Name;
    public string? Description => _i.Description;
    public string? ReformPoint => _i.ReformPoint;

    public static readonly IReadOnlyList<int> LevelOptions = new[] { 1, 2, 3, 4 };

    /// <summary>实例属性（WPF 绑定无法解析静态属性）</summary>
    public IReadOnlyList<int> Levels => LevelOptions;

    public int Level
    {
        get => _i.Level;
        set { _i.Level = value; Set(ref _lvl, value); }
    }
    private int _lvl;

    public string LevelText => _i.Level switch
    {
        1 => "I · 草创",
        2 => "II · 初具",
        3 => "III · 完备",
        4 => "IV · 极致",
        _ => "?"
    };

    public override void Recalculate(Nation n) => Raise(nameof(LevelText));
}
