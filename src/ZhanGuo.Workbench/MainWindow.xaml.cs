using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using ZhanGuo.Core.Changes;
using ZhanGuo.Core.Model;
using ZhanGuo.Core.Rules;
using ZhanGuo.Core.Serialization;
using ZhanGuo.Workbench.ViewModels;

namespace ZhanGuo.Workbench;

/// <summary>「对象」下拉项：把 (种类, 国, 实体) 三元组包装成可显示的一行。</summary>
public sealed class TargetItem
{
    public string Display { get; init; } = "";
    public EntityKind Kind { get; init; }
    public string? NationId { get; init; }
    public string? EntityId { get; init; }
    public DataRef ToRef() => new(Kind, NationId, EntityId);
    public override string ToString() => Display;
}

public sealed class FieldItem
{
    public FieldId Id { get; init; }
    public string Display { get; init; } = "";
    public override string ToString() => Display;
}

public sealed class PendingRow
{
    public ChangeOp Op { get; init; } = new();
    public string Text { get; init; } = "";
    public string Memo => Op.Memo;
    public override string ToString() => Text;
}

public partial class MainWindow : Window
{
    private GameState _state = new();
    private Nation? _nation;
    private string _statePath = "";
    private Dictionary<string, Dictionary<string, JsonElement>> _reference = new();

    private readonly ChangeSet _pending = new();
    private readonly ObservableCollection<PendingRow> _pendingRows = new();

    private readonly ObservableCollection<TaxRow> _taxes = new();
    private readonly ObservableCollection<ExpenseRow> _expenses = new();
    private readonly ObservableCollection<GroupRow> _groups = new();
    private readonly ObservableCollection<ArmyRow> _armies = new();
    private readonly ObservableCollection<InstitutionRow> _institutions = new();
    private readonly List<Situation> _situations = new();

    private bool _syncing;

    public MainWindow()
    {
        InitializeComponent();

        TaxGrid.ItemsSource = _taxes;
        ExpenseGrid.ItemsSource = _expenses;
        GroupGrid.ItemsSource = _groups;
        ArmyGrid.ItemsSource = _armies;
        InstGrid.ItemsSource = _institutions;
        SituationGrid.ItemsSource = _situations;
        PendingGrid.ItemsSource = _pendingRows;

        HookRowEvents();
        Loaded += (_, _) => LoadState(ResolveStatePath());
    }

    private void HookRowEvents()
    {
        foreach (var r in _taxes) r.Edited = Recompute;
        foreach (var r in _expenses) r.Edited = Recompute;
        foreach (var r in _groups) r.Edited = Recompute;
        foreach (var r in _armies) r.Edited = Recompute;
        foreach (var r in _institutions) r.Edited = Recompute;
    }

    // ---------------- 载入 ----------------

    private static string ResolveStatePath()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 8 && dir != null; i++, dir = dir.Parent)
        {
            var candidate = Path.Combine(dir.FullName, "data", "state.json");
            if (File.Exists(candidate)) return candidate;
        }
        return Path.Combine(Directory.GetCurrentDirectory(), "data", "state.json");
    }

    private void LoadState(string path)
    {
        try
        {
            if (!File.Exists(path)) { StatusText.Text = $"找不到状态文件：{path}"; return; }
            _statePath = path;
            _state = StateLoader.Load(path);
            LoadReference();

            _syncing = true;
            NationList.ItemsSource = _state.Nations;
            NationBox.ItemsSource = _state.Nations;
            FromNationBox.ItemsSource = _state.Nations;
            ToNationBox.ItemsSource = _state.Nations;
            TurnBox.Text = _state.Turn.ToString();
            _syncing = false;

            var first = _state.Nations.FirstOrDefault();
            if (first is not null)
            {
                NationList.SelectedItem = first;
                NationBox.SelectedItem = first;
                FromNationBox.SelectedItem = first;
                ToNationBox.SelectedItem = _state.Nations.Skip(1).FirstOrDefault() ?? first;
                BindNation(first);
            }
            StatusText.Text = $"已载入 {_state.Nations.Count} 国";
        }
        catch (Exception ex)
        {
            StatusText.Text = "载入失败：" + ex.Message;
        }
    }

    private void LoadReference()
    {
        _reference = new();
        var refPath = Path.Combine(Path.GetDirectoryName(_statePath)!, "excel_reference.json");
        if (!File.Exists(refPath)) return;
        try
        {
            _reference = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, JsonElement>>>(
                File.ReadAllText(refPath)) ?? new();
        }
        catch { /* 参考文件坏了不影响主流程 */ }
    }

    // ---------------- 绑定 ----------------

    private void BindNation(Nation n)
    {
        _nation = n;
        _taxes.Clear(); _expenses.Clear(); _groups.Clear(); _armies.Clear(); _institutions.Clear();
        _situations.Clear();

        foreach (var t in n.Taxes) _taxes.Add(new TaxRow(t));
        foreach (var e in n.Expenses) _expenses.Add(new ExpenseRow(e));
        foreach (var g in n.PopulationGroups) _groups.Add(new GroupRow(n, g));
        foreach (var a in n.Armies) _armies.Add(new ArmyRow(a));
        foreach (var i in n.Institutions) _institutions.Add(new InstitutionRow(i));
        foreach (var s in n.Situations) _situations.Add(s);

        HookRowEvents();
        BuildOverview(n);
        RefreshTargets();
        Recompute();
    }

    /// <summary>把当前国的所有可编辑对象铺成一张清单。</summary>
    private static List<TargetItem> BuildTargets(Nation n)
    {
        var list = new List<TargetItem>
        {
            new() { Display = "【国】整体", Kind = EntityKind.Nation, NationId = n.Id },
        };
        foreach (var g in n.PopulationGroups)
            list.Add(new() { Display = "人群 · " + g.Name, Kind = EntityKind.Group, NationId = n.Id, EntityId = g.Id });
        foreach (var t in n.Taxes)
            list.Add(new() { Display = "税目 · " + t.Name, Kind = EntityKind.Tax, NationId = n.Id, EntityId = t.Id });
        foreach (var e in n.Expenses)
            list.Add(new() { Display = $"开支 · {e.Name}（{(e.Kind == ExpenseKind.Project ? "工程" : "修正")}）", Kind = EntityKind.Expense, NationId = n.Id, EntityId = e.Id });
        foreach (var a in n.Armies)
            list.Add(new() { Display = "军队 · " + a.Name, Kind = EntityKind.Army, NationId = n.Id, EntityId = a.Id });
        foreach (var i in n.Institutions)
            list.Add(new() { Display = "制度 · " + i.Name, Kind = EntityKind.Institution, NationId = n.Id, EntityId = i.Id });
        return list;
    }

    private void RefreshTargets()
    {
        if (_nation is null) return;
        var items = BuildTargets(_nation);
        var keep = (ObjectBox.SelectedItem as TargetItem)?.EntityId;
        ObjectBox.ItemsSource = items;
        ObjectBox.SelectedItem = items.FirstOrDefault(x => x.EntityId == keep) ?? items.FirstOrDefault();
        RefreshFields();
        RefreshToObjects();
    }

    private void RefreshFields()
    {
        if (ObjectBox.SelectedItem is not TargetItem ti) return;
        var cur = (FieldBox.SelectedItem as FieldItem)?.Id;
        var list = FieldMeta.For(ti.Kind).Select(f => new FieldItem { Id = f, Display = FieldMeta.DisplayOf(f) }).ToList();
        FieldBox.ItemsSource = list;
        FieldBox.SelectedItem = list.FirstOrDefault(x => x.Id == cur) ?? list.FirstOrDefault();
    }

    private void RefreshToObjects()
    {
        if (ToNationBox.SelectedItem is not Nation to) return;
        var srcKind = (ObjectBox.SelectedItem as TargetItem)?.Kind ?? EntityKind.Group;
        var list = BuildTargets(to).Where(x => x.Kind == srcKind).ToList();
        ToObjectBox.ItemsSource = list;
        ToObjectBox.SelectedItem = list.FirstOrDefault();
        ToObjectBox.IsEnabled = !(CreateNewCheck.IsChecked == true);
    }

    private void BuildOverview(Nation n)
    {
        OverviewPanel.Children.Clear();

        OverviewPanel.Children.Add(new TextBlock
        {
            Text = n.Name + " 国", FontSize = 22, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 0, 4)
        });
        OverviewPanel.Children.Add(new TextBlock
        {
            Text = "此页为只读。要改数据请到「变更单」页写加减量。",
            Foreground = System.Windows.Media.Brushes.Gray, Margin = new Thickness(0, 0, 0, 16)
        });

        AddOverviewRow("预备兵力", () => n.Reserve, "N0");
        AddOverviewRow("行政建设", () => n.AdminLevel, "N2");
        AddOverviewRow("军治清明", () => n.MilitaryDiscipline, "N2");
        AddOverviewRow("官僚腐化", () => n.Corruption, "N2");
        AddOverviewRow("国库存量", () => n.Treasury, "N0");
    }

    private void AddOverviewRow(string label, Func<double> get, string fmt)
    {
        var p = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 8) };
        p.Children.Add(new TextBlock { Text = label, Width = 180, Foreground = System.Windows.Media.Brushes.Gray });
        p.Children.Add(new TextBlock
        {
            Text = get().ToString(fmt, CultureInfo.InvariantCulture),
            FontWeight = FontWeights.Bold
        });
        OverviewPanel.Children.Add(p);
    }

    // ---------------- 重算 ----------------

    private void Recompute()
    {
        if (_nation is null) return;

        foreach (var r in _taxes) r.Recalculate(_nation);
        foreach (var r in _groups) r.Recalculate(_nation);
        foreach (var r in _armies) r.Recalculate(_nation);
        foreach (var r in _institutions) r.Recalculate(_nation);

        BuildTotals(Economy.Totals(_nation));
    }

    private void BuildTotals(NationTotals t)
    {
        TotalsPanel.Children.Clear();
        TotalsPanel.Children.Add(new TextBlock
        {
            Text = "结算明细", FontSize = 16, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 0, 10)
        });

        AddTotal("人口", t.Population, "N0", "#8AB4F8");
        AddTotal("总税收", t.TotalTax, "N1", "#7DD3A0");
        AddTotal("军事开支", t.MilitaryExpense, "N1", "#E0A458");
        AddTotal("行政开支", t.AdminExpense, "N1", "#E0A458");
        AddTotal("工程开支", t.ProjectExpense, "N1", "#C98B8B");
        AddTotal("判定修正", t.ModifierTotal, "N1", "#B4A7D6");

        TotalsPanel.Children.Add(new Border
        {
            Height = 1, Background = System.Windows.Media.Brushes.DimGray, Margin = new Thickness(0, 8, 0, 8)
        });

        AddTotal("总结余", t.Balance, "N1", t.Balance >= 0 ? "#7DD3A0" : "#F27A7A", big: true);
        AddTotal("国库存量", t.Treasury, "N0", "#8AB4F8");

        if (t.TotalTax > 0)
        {
            TotalsPanel.Children.Add(new TextBlock
            {
                Text = $"行政占税收 {t.AdminExpense / t.TotalTax:P0} · 军事占税收 {t.MilitaryExpense / t.TotalTax:P0}",
                Foreground = System.Windows.Media.Brushes.Gray, Margin = new Thickness(0, 12, 0, 0),
                TextWrapping = TextWrapping.Wrap
            });
        }
    }

    private void AddTotal(string label, double value, string format, string color, bool big = false)
    {
        var panel = new StackPanel { Margin = new Thickness(0, 0, 0, 8) };
        panel.Children.Add(new TextBlock { Text = label, Foreground = System.Windows.Media.Brushes.Gray, FontSize = 12 });
        var brush = (System.Windows.Media.Brush)new System.Windows.Media.BrushConverter().ConvertFromString(color)!;
        panel.Children.Add(new TextBlock
        {
            Text = value.ToString(format, CultureInfo.InvariantCulture),
            FontSize = big ? 24 : 17,
            FontWeight = big ? FontWeights.Bold : FontWeights.Normal,
            Foreground = brush
        });
        TotalsPanel.Children.Add(panel);
    }

    // ---------------- 变更单 ----------------

    private void OpKindBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ToPanel is null) return; // 构造期
        var isTransfer = CurrentOpKind() == OpKind.Transfer;
        ToPanel.Visibility = isTransfer ? Visibility.Visible : Visibility.Collapsed;
        ToObjPanel.Visibility = isTransfer ? Visibility.Visible : Visibility.Collapsed;
        CreatePanel.Visibility = isTransfer ? Visibility.Visible : Visibility.Collapsed;
        if (isTransfer) RefreshToObjects();
    }

    private OpKind CurrentOpKind()
    {
        if (OpKindBox.SelectedItem is ComboBoxItem item && item.Tag is string tag)
            return tag switch
            {
                "Transfer" => OpKind.Transfer,
                "Set" => OpKind.Set,
                _ => OpKind.Adjust
            };
        return OpKind.Adjust;
    }

    private void FromNationBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing) return;
        if (FromNationBox.SelectedItem is Nation n)
        {
            ObjectBox.ItemsSource = BuildTargets(n);
            ObjectBox.SelectedItem = ObjectBox.Items.Cast<TargetItem>().FirstOrDefault();
            RefreshFields();
        }
    }

    private void ObjectBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        RefreshFields();
        if (CurrentOpKind() == OpKind.Transfer) RefreshToObjects();
    }

    private void ToNationBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CurrentOpKind() == OpKind.Transfer) RefreshToObjects();
    }

    private void AddOp_Click(object sender, RoutedEventArgs e)
    {
        if (ObjectBox.SelectedItem is not TargetItem ti)
        {
            StatusText.Text = "请先选对象"; return;
        }
        if (FieldBox.SelectedItem is not FieldItem fi)
        {
            StatusText.Text = "请先选字段"; return;
        }
        if (!double.TryParse(ValueBox.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
        {
            StatusText.Text = "数值不合法"; return;
        }
        if (string.IsNullOrWhiteSpace(MemoBox.Text))
        {
            StatusText.Text = "必须填写事由"; return;
        }

        var kind = CurrentOpKind();
        var op = new ChangeOp
        {
            Kind = kind,
            Target = ti.ToRef(),
            Field = fi.Id,
            Value = value,
            Memo = MemoBox.Text.Trim(),
        };

        if (kind == OpKind.Transfer)
        {
            if (ToNationBox.SelectedItem is not Nation toNation)
            {
                StatusText.Text = "请选择目标国"; return;
            }
            if (value <= 0)
            {
                StatusText.Text = "转移数量必须为正数"; return;
            }

            if (CreateNewCheck.IsChecked == true)
            {
                if (ti.Kind != EntityKind.Group)
                {
                    StatusText.Text = "只有人群支持自动新建"; return;
                }
                op.To = new DataRef(EntityKind.Group, toNation.Id, "gNew" + DateTime.Now.Ticks);
                op.CreateIfMissing = true;
            }
            else
            {
                if (ToObjectBox.SelectedItem is not TargetItem toItem)
                {
                    StatusText.Text = "请选择目标对象"; return;
                }
                op.To = toItem.ToRef();
            }
        }

        _pending.Ops.Add(op);
        RefreshPending();
        MemoBox.Clear();
        ValueBox.Text = "0";
        StatusText.Text = $"已加入变更单（{_pending.Ops.Count} 条待提交）";
        PreviewText.Text = "（尚未预览）";
    }

    private void RefreshPending()
    {
        _pendingRows.Clear();
        foreach (var op in _pending.Ops)
        {
            var text = op.Describe();
            if (op.Kind == OpKind.Transfer && op.To is not null)
                text = $"{op.Target.Describe(_state)} 的 {FieldMeta.DisplayOf(op.Field)} 转出 {op.Value:0.##} → {op.To.Describe(_state)}";
            else
                text = $"{op.Target.Describe(_state)}  {text}";

            _pendingRows.Add(new PendingRow { Op = op, Text = text });
        }
    }

    private void RemoveOp_Click(object sender, RoutedEventArgs e)
    {
        if (PendingGrid.SelectedItem is PendingRow row)
        {
            _pending.Ops.Remove(row.Op);
            RefreshPending();
            PreviewText.Text = "（尚未预览）";
        }
    }

    private void ClearOps_Click(object sender, RoutedEventArgs e)
    {
        _pending.Ops.Clear();
        RefreshPending();
        PreviewText.Text = "（尚未预览）";
    }

    private void Preview_Click(object sender, RoutedEventArgs e)
    {
        if (_pending.Ops.Count == 0) { PreviewText.Text = "变更单是空的。"; return; }
        var deltas = _pending.Preview(_state, out var error);
        if (error is not null)
        {
            PreviewText.Text = "❌ " + error;
            return;
        }
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"将产生 {deltas.Count} 处数值变化：\n");
        foreach (var d in deltas) sb.AppendLine("  " + d.Text);
        sb.AppendLine($"\n状态哈希（提交前）：{ChangeSet.Hash(_state)}");
        PreviewText.Text = sb.ToString();
    }

    private void Commit_Click(object sender, RoutedEventArgs e)
    {
        if (_pending.Ops.Count == 0) { StatusText.Text = "变更单是空的"; return; }

        var beforeHash = ChangeSet.Hash(_state);
        var snapshot = _pending.Ops.ToList();
        var deltas = _pending.Preview(_state, out var error);
        if (error is not null) { StatusText.Text = "提交被拒：" + error; return; }

        var count = _pending.Commit(_state, out error);
        if (count < 0) { StatusText.Text = "提交被拒：" + error; return; }

        var afterHash = ChangeSet.Hash(_state);
        AppendEventLog(snapshot, deltas, beforeHash, afterHash);

        _pending.Ops.Clear();
        RefreshPending();
        PreviewText.Text = $"✅ 已提交 {count} 条变更\n状态哈希：{beforeHash} → {afterHash}\n已记入 data/events.jsonl";
        StatusText.Text = $"已提交 {count} 条变更";
        RebindAfterCommit();
    }

    private void AppendEventLog(IReadOnlyList<ChangeOp> ops, IReadOnlyList<FieldDelta> deltas,
                                string beforeHash, string afterHash)
    {
        try
        {
            var dir = Path.GetDirectoryName(_statePath)!;
            var path = Path.Combine(dir, "events.jsonl");
            var record = new
            {
                turn = _state.Turn,
                time = DateTime.Now.ToString("O"),
                beforeHash,
                afterHash,
                ops = ops.Select(o => new
                {
                    kind = o.Kind.ToString(),
                    target = new { kind = o.Target.Kind.ToString(), nation = o.Target.NationId, entity = o.Target.EntityId },
                    field = o.Field.ToString(),
                    value = o.Value,
                    to = o.To is null ? null : new { kind = o.To.Kind.ToString(), nation = o.To.NationId, entity = o.To.EntityId },
                    memo = o.Memo
                }),
                deltas = deltas.Select(d => new { where = d.Where, field = d.Field, before = d.Before, after = d.After })
            };
            File.AppendAllText(path, JsonSerializer.Serialize(record, StateLoader.Options) + Environment.NewLine);
        }
        catch (Exception ex)
        {
            StatusText.Text = "事件日志写入失败：" + ex.Message;
        }
    }

    private void RebindAfterCommit()
    {
        var keepId = _nation?.Id;
        _syncing = true;
        NationList.ItemsSource = null;
        NationBox.ItemsSource = null;
        FromNationBox.ItemsSource = null;
        ToNationBox.ItemsSource = null;
        NationList.ItemsSource = _state.Nations;
        NationBox.ItemsSource = _state.Nations;
        FromNationBox.ItemsSource = _state.Nations;
        ToNationBox.ItemsSource = _state.Nations;
        _syncing = false;

        var n = _state.Find(keepId ?? "") ?? _state.Nations.FirstOrDefault();
        if (n is not null)
        {
            _syncing = true;
            NationList.SelectedItem = n;
            NationBox.SelectedItem = n;
            FromNationBox.SelectedItem = n;
            if (ToNationBox.SelectedItem is null) ToNationBox.SelectedItem = _state.Nations.FirstOrDefault();
            _syncing = false;
            BindNation(n);
        }
    }

    // ---------------- 顶栏 ----------------

    private void NationList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing) return;
        if (NationList.SelectedItem is Nation n) { SyncNationSelection(n); BindNation(n); }
    }

    private void NationBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing) return;
        if (NationBox.SelectedItem is Nation n) { SyncNationSelection(n); BindNation(n); }
    }

    private void SyncNationSelection(Nation n)
    {
        _syncing = true;
        NationList.SelectedItem = n;
        NationBox.SelectedItem = n;
        FromNationBox.SelectedItem = n;
        _syncing = false;
    }

    private void TurnBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (int.TryParse(TurnBox.Text, out var v)) _state.Turn = v;
        else TurnBox.Text = _state.Turn.ToString();
    }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            StateLoader.Save(_state, _statePath);
            StatusText.Text = $"已保存 · {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex) { StatusText.Text = "保存失败：" + ex.Message; }
    }

    private void Reload_Click(object sender, RoutedEventArgs e) => LoadState(_statePath);

    private void Verify_Click(object sender, RoutedEventArgs e)
    {
        if (_nation is null) return;
        if (!_reference.TryGetValue(_nation.Id, out var r)) { StatusText.Text = "没有该国的 Excel 参考值"; return; }
        double R(string k) => r.TryGetValue(k, out var el) ? el.GetDouble() : double.NaN;
        var t = Economy.Totals(_nation);
        var pairs = new (string Name, double A, double B)[]
        {
            ("人口", t.Population, R("population")),
            ("总税收", t.TotalTax, R("totalTax")),
            ("军事开支", t.MilitaryExpense, R("militaryExpense")),
            ("行政开支", t.AdminExpense, R("adminExpense")),
            ("总结余", t.Balance, R("balance")),
        };
        var bad = pairs.Count(p => Math.Abs(p.A - p.B) / Math.Max(1, Math.Abs(p.B)) > 1e-6);
        StatusText.Text = bad == 0
            ? "与 Excel 完全一致 ✅"
            : $"有 {bad} 项与 Excel 不一致（说明你改过数据，或公式有偏差）";
    }
}
