using System.Text;
using System.Text.Json;
using ZhanGuo.Core.Rules;
using ZhanGuo.Core.Serialization;

// 公式复现校验：把 C# 算出来的值与 Excel 缓存值逐项对比。
// 用法: dotnet run --project src/ZhanGuo.Verify -- <repoRoot>

var root = args.Length > 0 ? args[0] : Directory.GetCurrentDirectory();

// 子命令：changes = 变更单行为测试
if (args.Length > 1 && args[1] == "changes")
    return ZhanGuo.Verify.ChangeTests.Run(root);

var state = StateLoader.Load(Path.Combine(root, "data", "state.json"));
var refJson = File.ReadAllText(Path.Combine(root, "data", "excel_reference.json"));
var reference = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, JsonElement>>>(refJson)!;

var sb = new StringBuilder();
var failures = 0;
var checks = 0;
var worst = 0.0;
string worstDesc = "";

static double Rel(double a, double b)
{
    var d = Math.Abs(a - b);
    var scale = Math.Max(1.0, Math.Max(Math.Abs(a), Math.Abs(b)));
    return d / scale;
}

void Check(string nation, string field, double actual, double expected)
{
    checks++;
    var rel = Rel(actual, expected);
    if (rel > worst) { worst = rel; worstDesc = $"{nation}.{field}: got {actual}, expected {expected}"; }
    if (rel > 1e-6)
    {
        failures++;
        sb.AppendLine($"  [差异] {nation,-4} {field,-22} 计算={actual:G17}  Excel={expected:G17}  相对差={rel:E3}");
    }
}

sb.AppendLine("=== 公式复现校验 ===");
sb.AppendLine($"状态文件: data/state.json  回合={state.Turn}");
sb.AppendLine();

foreach (var n in state.Nations)
{
    if (!reference.TryGetValue(n.Id, out var r))
    {
        sb.AppendLine($"  [缺失] 参考值里没有 {n.Id}");
        failures++;
        continue;
    }
    double R(string k) => r.TryGetValue(k, out var e) ? e.GetDouble() : double.NaN;

    var t = Economy.Totals(n);
    Check(n.Name, "population", t.Population, R("population"));
    Check(n.Name, "totalTax", t.TotalTax, R("totalTax"));
    Check(n.Name, "militaryExpense", t.MilitaryExpense, R("militaryExpense"));
    Check(n.Name, "adminExpense", t.AdminExpense, R("adminExpense"));
    Check(n.Name, "balance", t.Balance, R("balance"));
    Check(n.Name, "treasury", t.Treasury, R("treasury"));

    // 税基 / 上税
    if (r.TryGetValue("taxBase", out var tb))
    {
        var arr = tb.EnumerateArray().Select(x => x.GetDouble()).ToArray();
        for (var i = 0; i < Math.Min(arr.Length, n.Taxes.Count); i++)
            Check(n.Name, $"taxBase[{n.Taxes[i].Name}]", Economy.TaxBase(n, n.Taxes[i]), arr[i]);
    }
    if (r.TryGetValue("taxPaid", out var tp))
    {
        var arr = tp.EnumerateArray().Select(x => x.GetDouble()).ToArray();
        for (var i = 0; i < Math.Min(arr.Length, n.Taxes.Count); i++)
            Check(n.Name, $"taxPaid[{n.Taxes[i].Name}]", Economy.TaxPaid(n.Taxes[i]), arr[i]);
    }

    // 人群人口 / 产值
    if (r.TryGetValue("groupPopulation", out var gp))
    {
        var arr = gp.EnumerateArray().Select(x => x.GetDouble()).ToArray();
        for (var i = 0; i < Math.Min(arr.Length, n.PopulationGroups.Count); i++)
            Check(n.Name, $"pop[{n.PopulationGroups[i].Name}]", Economy.Population(n, n.PopulationGroups[i]), arr[i]);
    }
    if (r.TryGetValue("groupOutput", out var go))
    {
        var arr = go.EnumerateArray().Select(x => x.GetDouble()).ToArray();
        for (var i = 0; i < Math.Min(arr.Length, n.PopulationGroups.Count); i++)
            Check(n.Name, $"output[{n.PopulationGroups[i].Name}]", Economy.Output(n, n.PopulationGroups[i]), arr[i]);
    }

    // 军队维护费
    if (r.TryGetValue("armyUpkeep", out var au))
    {
        var arr = au.EnumerateArray().Select(x => x.GetDouble()).ToArray();
        for (var i = 0; i < Math.Min(arr.Length, n.Armies.Count); i++)
            Check(n.Name, $"upkeep[{n.Armies[i].Name}]", Economy.Upkeep(n.Armies[i]), arr[i]);
    }

    sb.AppendLine($"  {n.Name,-4} 人口={t.Population,10:N0}  税收={t.TotalTax,10:N1}  " +
                  $"军费={t.MilitaryExpense,9:N1}  行政={t.AdminExpense,10:N1}  结余={t.Balance,9:N1}");
}

sb.AppendLine();
sb.AppendLine($"共校验 {checks} 项，超出容差 {failures} 项");
sb.AppendLine($"最大相对偏差 {worst:E3}  ({worstDesc})");
sb.AppendLine(failures == 0 ? "结论：公式复现通过 ✅" : "结论：存在差异 ❌");

var reportPath = Path.Combine(root, "tools", "_verify.log");
Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);
File.WriteAllText(reportPath, sb.ToString(), new UTF8Encoding(false));

Console.WriteLine($"checks={checks} failures={failures} maxrel={worst:E3}");
Console.WriteLine(failures == 0 ? "PASS" : "FAIL");
Console.WriteLine($"report -> {reportPath}");
return failures == 0 ? 0 : 1;
