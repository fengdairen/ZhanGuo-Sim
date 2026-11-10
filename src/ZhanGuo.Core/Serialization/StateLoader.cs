using System.Text.Json;
using System.Text.Json.Serialization;
using ZhanGuo.Core.Model;

namespace ZhanGuo.Core.Serialization;

/// <summary>状态读写。JSON 是权威格式，Excel 只在导出时出现。</summary>
public static class StateLoader
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        Converters = { new JsonStringEnumConverter() },
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    public static GameState Load(string path)
    {
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<GameState>(json, Options)
               ?? throw new InvalidDataException($"无法解析状态文件: {path}");
    }

    public static void Save(GameState state, string path)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, JsonSerializer.Serialize(state, Options));
    }
}
