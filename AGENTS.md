# AGENTS.md — 工作区约定

本文件给任何接手本工作区的 AI 助手看。

## 第一件事

**按顺序读 `docs/00-项目总览.md`，再看 `docs/README.md` 索引。**
那一份包含：用户画像、项目目标、五层架构摘要、崇祯的结构与教训、现有资产、已拍板/未定事项、工程铁律、协作偏好。

不要跳过它直接动手。

## 项目一句话

《战国演义》——单机战国文字国策模拟。玩家写国策 → LLM 解析成结构化意图 → 确定性代码结算五层 → 奏报回玩家。

## 当前阶段

**M0 已完成**：`ZhanGuo.Core` 已能脱离 Excel 计算全部公式，校验器 284 项全通过、偏差 0。
**地图层数据已完成**：1040 城邑（30 都 / 61 城 / 949 邑）+ 54 部族，全部命名、已填人口与归属（见 `docs/2-数据/21-地图-城邑与部族.md`）。
下一步 M1：回合推进 + 事件日志 + 回放（仍不接 LLM）。

## 已知风险（动手前先看）

见 `docs/3-工程/32-风险与评审.md`：

1. **`data/events.jsonl` 从未生成**——变更单写入链路"测过但没用过"，M1 前必须真跑一次
2. **文档的状态段最容易腐坏**——推进里程碑时务必回头改「当前状态」这类段落
3. **推送需要 `danger-full-access`**——沙箱禁止创建管道，`git push` 会报 `couldn't create signal pipe`

## 工作区结构

```
/
├── 启动数据台.cmd / 重建地图.cmd    两个入口
├── 备份.xlsm                       数据模板（只读参考，别改）
├── assets/                         源图与 PSD（source/ 七张原图、ditu.psd，不进库）
├── data/                           state.json + map/（城邑/部族/人口/归属/经济 + rivers/ vector/）
├── dist/                           产物：index.html、river-editor/、map-review/、map-vector/
├── docs/                           00 入口 + 1-设计 … 6-推演记录（见 docs/README.md）
├── materials/                      用户提供的原始材料（推演风格 / 军事设计）
├── src/                            Core（纯公式）/ Workbench（WPF）/ Verify（校验器）
├── tools/
│   ├── pipeline/                   当前在用的脚本（21 个）
│   ├── smoke/                      冒烟测试（3 个）
│   └── legacy/                     历史脚本（47 个，不再维护）
```

**新增文件前先看 `docs/3-工程/33-目录结构.md`。**

## 构建与运行

构建前必须重定向 .NET 的写目录（沙箱不允许写用户目录）：

```powershell
$env:DOTNET_CLI_HOME = "<repo>\.cache\dotnet"
$env:NUGET_PACKAGES  = "<repo>\.nuget\packages"
$env:DOTNET_CLI_UI_LANGUAGE = 'en'   # 中文错误信息在 GBK 控制台下会乱码

dotnet build src\ZhanGuo.Workbench -c Release
dotnet run  --project src\ZhanGuo.Verify -- <repo>    # 公式校验，exit 0 即通过
python tools\pipeline\export_state.py                          # xlsm → JSON
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

理由见 `docs/4-决策/40-决策日志.md`。

