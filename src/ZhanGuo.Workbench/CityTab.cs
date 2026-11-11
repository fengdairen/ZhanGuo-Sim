using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using ZhanGuo.Core.Model;

namespace ZhanGuo.Workbench;

/// <summary>城池行（地图层）。归属存国别 id，显示用中文名。</summary>
public sealed class CityRow
{
    public string Id { get; init; } = "";
    public string Name { get; init; } = "";
    public string Kind { get; init; } = "";
    public double Pop { get; set; }
    public double X { get; init; }
    public double Y { get; init; }
    public string OwnerId { get; set; } = "";
    public string OwnerName { get; set; } = "";
    public string Owner => string.IsNullOrEmpty(OwnerId) ? "（未归属）" : OwnerName;
    public string Pos => $"{(int)X},{(int)Y}";
}

/// <summary>城池页：读 nodes.csv + ownership.csv，支持筛选与批量分配归属。</summary>
public partial class MainWindow
{
    private readonly ObservableCollection<CityRow> _cityView = new();
    private readonly List<CityRow> _cityAll = new();
    private readonly ObservableCollection<string> _kindChoices = new();
    private readonly ObservableCollection<string> _ownerChoices = new();
    private readonly ObservableCollection<Nation> _assignNations = new();
    private string _ownershipPath = "";
    private bool _cityReady;
    private readonly List<string> _allIds = new();
    private readonly Dictionary<string, string> _ownerRaw = new();

    /// <summary>在 LoadState 末尾调用一次。</summary>
    private void InitCityTab(string statePath)
    {
        if (_cityReady) return;
        _cityReady = true;

        CityGrid.ItemsSource = _cityView;
        CityKind.ItemsSource = _kindChoices;
        CityOwnerFilter.ItemsSource = _ownerChoices;
        CityAssignTo.ItemsSource = _assignNations;

        _kindChoices.Add("全部");
        foreach (var k in new[] { "都", "城", "邑", "部族" }) _kindChoices.Add(k);
        CityKind.SelectedIndex = 0;

        _ownerChoices.Add("全部");
        _ownerChoices.Add("（未归属）");
        foreach (var n in _state.Nations) { _assignNations.Add(n); _ownerChoices.Add(n.Name); }
        CityOwnerFilter.SelectedIndex = 0;
        if (_assignNations.Count > 0) CityAssignTo.SelectedIndex = 0;

        var mapDir = Path.Combine(Path.GetDirectoryName(statePath)!, "map");
        _ownershipPath = Path.Combine(mapDir, "ownership.csv");
        LoadCities(mapDir);
    }

    private void LoadCities(string mapDir)
    {
        _cityAll.Clear();
        _allIds.Clear();
        _ownerRaw.Clear();
        var nodes = Path.Combine(mapDir, "nodes.csv");
        if (!File.Exists(nodes)) { CityStat.Text = $"找不到 {nodes}"; return; }

        if (File.Exists(_ownershipPath))
        {
            foreach (var cells in ReadCsv(_ownershipPath).Skip(1))
                if (cells.Count >= 2 && cells[0].Length > 0) _ownerRaw[cells[0]] = cells[1];
        }

        var byId = _state.Nations.ToDictionary(n => n.Id, n => n.Name);
        foreach (var cells in ReadCsv(nodes).Skip(1))
        {
            if (cells.Count < 5) continue;
            var id = cells[0];
            _allIds.Add(id);                       // 全量 id，含部族，保存时原样写回
            var kind = cells[2];
            if (kind == "部族") continue;          // 城池页只管城邑
            _ownerRaw.TryGetValue(id, out var oid);
            _cityAll.Add(new CityRow
            {
                Id = id,
                Name = cells[1],
                Kind = kind,
                X = ParseD(cells[3]),
                Y = ParseD(cells[4]),
                Pop = cells.Count > 5 ? ParseD(cells[5]) : 0,
                OwnerId = oid ?? "",
                OwnerName = oid is not null && byId.TryGetValue(oid, out var nm) ? nm : ""
            });
        }
        ApplyCityFilter();
    }

    private static double ParseD(string s) =>
        double.TryParse(s, System.Globalization.NumberStyles.Any,
            System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : 0;

    private void ApplyCityFilter()
    {
        var q = (CitySearch.Text ?? "").Trim();
        var kind = CityKind.SelectedItem as string;
        var own = CityOwnerFilter.SelectedItem as string;

        _cityView.Clear();
        foreach (var c in _cityAll)
        {
            if (kind is not null && kind != "全部" && c.Kind != kind) continue;
            if (own is not null && own != "全部")
            {
                if (own == "（未归属）") { if (c.OwnerId.Length > 0) continue; }
                else if (c.OwnerName != own) continue;
            }
            if (q.Length > 0 && c.Name.IndexOf(q, StringComparison.Ordinal) < 0
                            && c.Id.IndexOf(q, StringComparison.OrdinalIgnoreCase) < 0) continue;
            _cityView.Add(c);
        }
        var assigned = _cityAll.Count(c => c.OwnerId.Length > 0);
        CityStat.Text = $"共 {_cityAll.Count} 座，已归属 {assigned}，未归属 {_cityAll.Count - assigned}；当前显示 {_cityView.Count}";
    }

    private void CitySearch_Changed(object sender, TextChangedEventArgs e) { if (_cityReady) ApplyCityFilter(); }
    private void CityFilter_Changed(object sender, SelectionChangedEventArgs e) { if (_cityReady) ApplyCityFilter(); }

    private void AssignOwner_Click(object sender, RoutedEventArgs e)
    {
        var n = CityAssignTo.SelectedItem as Nation;
        if (n is null) { StatusText.Text = "请选择要分配到的国家"; return; }
        var picked = CityGrid.SelectedItems.Cast<CityRow>().ToList();
        if (picked.Count == 0) { StatusText.Text = "请先在列表中选择城池（可多选）"; return; }
        foreach (var c in picked) { c.OwnerId = n.Id; c.OwnerName = n.Name; }
        SaveOwnership();
        ApplyCityFilter();
        StatusText.Text = $"已把 {picked.Count} 座城邑分配给 {n.Name}";
    }

    private void ClearOwner_Click(object sender, RoutedEventArgs e)
    {
        var picked = CityGrid.SelectedItems.Cast<CityRow>().ToList();
        if (picked.Count == 0) return;
        foreach (var c in picked) { c.OwnerId = ""; c.OwnerName = ""; }
        SaveOwnership();
        ApplyCityFilter();
        StatusText.Text = $"已清除 {picked.Count} 座城邑的归属";
    }

    private void SaveOwner_Click(object sender, RoutedEventArgs e)
    {
        SaveOwnership();
        StatusText.Text = "归属已写入 " + _ownershipPath;
    }

    private void SaveOwnership()
    {
        foreach (var c in _cityAll) _ownerRaw[c.Id] = c.OwnerId;
        var sb = new System.Text.StringBuilder();
        sb.Append('\uFEFF').AppendLine("city_id,owner,note");
        foreach (var id in _allIds)
        {
            _ownerRaw.TryGetValue(id, out var o);
            sb.AppendLine($"{id},{o},");
        }
        File.WriteAllText(_ownershipPath, sb.ToString(), new System.Text.UTF8Encoding(false));
    }

    private void OpenInMap_Click(object sender, RoutedEventArgs e)
    {
        // 依次向上找 dist/map-review/map_editor.html
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 8 && dir is not null; i++, dir = dir.Parent)
        {
            var p = Path.Combine(dir.FullName, "dist", "map-review", "map_editor.html");
            if (File.Exists(p))
            {
                var sel = CityGrid.SelectedItems.Cast<CityRow>().FirstOrDefault();
                var url = sel is null ? p : p + "#" + sel.Id;
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
                StatusText.Text = sel is null ? "已打开地图编辑器" : $"已打开地图编辑器，定位 {sel.Name}";
                return;
            }
        }
        StatusText.Text = "找不到 map_editor.html";
    }

    // 极简 CSV 读取（本项目写出的 CSV 无引号逗号）
    private static IEnumerable<List<string>> ReadCsv(string path)
    {
        foreach (var line in File.ReadLines(path, System.Text.Encoding.UTF8))
        {
            if (line.Length == 0) continue;
            yield return line.TrimEnd('\r').Split(',').ToList();
        }
    }
}
