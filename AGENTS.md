# AGENTS.md — 工作区约定

本文件给任何接手本工作区的 AI 助手看。

## 第一件事

**按顺序读 `docs/00-总览与新会话须知.md`。**
那一份包含：用户画像、项目目标、五层架构摘要、崇祯的结构与教训、现有资产、已拍板/未定事项、工程铁律、协作偏好。

不要跳过它直接动手。

## 项目一句话

《战国演义》——单机战国文字国策模拟。玩家写国策 → LLM 解析成结构化意图 → 确定性代码结算五层 → 奏报回玩家。

## 当前阶段

**M0 已完成**：`ZhanGuo.Core` 已能脱离 Excel 计算全部公式，校验器 284 项全通过、偏差 0。
**地图层数据已完成**：1040 城邑（30 都 / 61 城 / 949 邑）+ 54 部族，全部命名、已填人口初值（见 `docs/15`）。
下一步 M1：回合推进 + 事件日志 + 回放（仍不接 LLM）。

## 已知风险（动手前先看）

见 `docs/16-工程风险与外部评审.md`：

1. **不是 git 仓库**——曾因写文件崩溃丢失用户 28 条勘误，现在只靠 `_backup_*.csv` 兜底
2. **`data/events.jsonl` 从未生成**——变更单写入链路"测过但没用过"，M1 前必须真跑一次
3. **文档的状态段最容易腐坏**——推进里程碑时务必回头改 §0/§5 这类"当前状态"

## 工作区结构

```
/
├── 备份.xlsm      数据模板（只读参考，别改）
├── data/          state.json（权威状态）+ excel_reference.json（校验基准）
├── dist/          ZhanGuo.Workbench.exe（可直接双击）
├── src/
│   ├── ZhanGuo.Core/      纯数据 + 公式，无 UI 依赖，可被任何引擎引用
│   ├── ZhanGuo.Workbench/ WPF 工作台
│   └── ZhanGuo.Verify/    命令行校验器
├── docs/          文档（00 是入口）
├── tools/         导出与校验脚本
└── tools/_*.txt   脚本生成的报告（可删）
```

## 构建与运行

构建前必须重定向 .NET 的写目录（沙箱不允许写用户目录）：

```powershell
$env:DOTNET_CLI_HOME = "<repo>\.dotnet"
$env:NUGET_PACKAGES  = "<repo>\.nuget\packages"
$env:DOTNET_CLI_UI_LANGUAGE = 'en'   # 中文错误信息在 GBK 控制台下会乱码

dotnet build src\ZhanGuo.Workbench -c Release
dotnet run  --project src\ZhanGuo.Verify -- <repo>    # 公式校验，exit 0 即通过
python tools\export_state.py                          # xlsm → JSON
```

## 环境备注（踩过的坑）

- Python 用 `load_workspace_dependencies` 返回的解释器路径，已装 openpyxl / pandas。
- **PowerShell 控制台输出中文会乱码**（GBK/UTF-8 混淆）。
  对策：脚本把结果写成 UTF-8 文件，再用 `read` 工具读；不要靠 stdout 看中文。
- `.xlsm` 用 `openpyxl.load_workbook(..., keep_vba=True)` 读取；**不要改名成 .xlsx**。
- VBA 源码是压缩存储的，直接抽字符串只能看到片段；目前已知宏只有辅助按钮（算账 / + / -）。
- **启动 GUI 进程必须重定向 stdio**，否则子进程继承管道会让命令挂起：
  ```powershell
  Start-Process $exe -PassThru -RedirectStandardOutput out.txt -RedirectStandardError err.txt
  ```
- **NuGet 在当前网络下不可达**（SSL 认证失败），所以不能做 self-contained / 单文件发布，
  只能框架依赖发布（需要本机 .NET 10 桌面运行时）。
- `dotnet new` 会因为写 `.dotnet` 哨兵文件而被沙箱拒绝；直接手写 `.csproj` 更省事。

## 文档约定

结论必须带标记：

- `[已证实]` — 有官方技术文、补丁日志或玩家实测佐证
- `[推测]` — 由现象反推，逻辑自洽但无直接证据
- `[判读]` — 作者的分析意见
- `[待验证]` — 需要实测或用户确认

## 工程铁律

1. 模型不碰模拟器（经济/军事的数值只能由代码写）
2. M0–M2 不接 LLM
3. Excel 是编辑期工具，运行期用 JSON/SQLite
4. 结算是纯函数，可回放，无副作用
5. 变更单必须带 `assumptions` 与 `unparsed`

## 协作偏好

- 先调研、再分析、最后动手；不要跳过论证直接给方案。
- 要具体数字和证据链，不要空泛设计辞藻。
- 金额/规模类判断必须绑定投入规模（曾因"20 万很少"被纠正）。
- 用户是先秦史内行 + 游戏策划 + C# 开发者：可以直接谈架构与实现，不要科普常识，也不要编历史细节。
- 中文交流。

## 已被否决的方案（不要重提）

- 群服 / 多人在线（用户要单机）
- 让 LLM 直接写数值字段
- 用超长上下文维持记忆
- Excel 作为运行期状态
- 先做游戏再考虑工具化

理由见 `docs/11-决策日志.md`。
