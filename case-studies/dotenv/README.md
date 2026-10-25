# python-dotenv：带引号的字符串写入/读取往返

2026-10-25 在 **python-dotenv 1.2.4** 上，独立 CLI 和修复后的真实 DSH 受限环境均完成 **2,500 次评估，`no_counterexample`**。DSH 内新导出属性测试加 14 个直接文件 API 样例得到 **15 passed in 11.64s**。本案例没有确认上游 bug；这不是“项目不存在 bug”的证明。

## DSH 受限环境修复与复验

首次 DSH 运行返回 `inconclusive / exit 2`，保存在[原始验证摘要](../dsh-verification.json)。同一测试在普通 CLI 成功，原因是测试目录权限与 DSH 受限令牌不兼容：

- [CPython 3.13 的 `mkdir(0o700)`](https://docs.python.org/3.13/library/os.html#os.mkdir)在 Windows 设置专有权限；`TemporaryDirectory` 使用该模式。实际检查到 6 个失败残留目录均启用受保护 DACL、继承规则数为 0；父案例目录有 5 条继承规则及 DSH 工作区授权。
- [Windows 受限令牌](https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens)需要额外通过 restricting SID 的访问检查，缺少继承授权会造成拒绝访问。
- [fixture_directory.py](fixture_directory.py)只为公开合成数据创建 UUID 唯一子目录。Windows 使用默认 `mkdir()` 继承项目已有 ACL，非 Windows 继续使用 `TemporaryDirectory`。`finally` 检查目录范围后严格清理，错误仍会上报；没有修改 ACL、令牌或全局沙箱配置。
- 执行器生成的独立测试原来也用 `TemporaryDirectory` 隔离旧字节码。现在缓存隔离使用不创建的唯一目录路径，保留禁止写入字节码和导入后恢复状态，避免引入第二处相同权限问题。已有导出及旧字节码检查共 9 项通过。

修复没有修改 python-dotenv 的 `set_key` / `dotenv_values`、规格 JSON、字符域、seed `20261025` 或预算 `2500`，也没有忽略清理错误。此次仅修复测试宿主与 DSH 权限模型的兼容性。

| DSH 实际检查 | 结果 |
| --- | --- |
| Skill / provider / model | `dsh-property-lab` / `deepseek-official` / `deepseek-flash` |
| 权限模式 / Python | `workspace-write` / 3.13.15 |
| [权限探针](probe_permissions.py) | `restricted_token=true`；`protected=false`；继承规则数 `5` |
| 合成目录操作 | 创建、写入、重命名、读取、删除均成功；`directory_removed=true` |
| 属性搜索 | `no_counterexample`，实际 `2500` 次，退出 `0`；引擎耗时 `10.221755 s` |
| 新导出测试 + 14 个直接 API 样例 | `15 passed in 11.64s`，退出 `0` |
| 本轮新增残留目录 | `0`；此前 6 个失败残留未触碰 |

[dsh-permission-fix.json](dsh-permission-fix.json)记录新会话的工具调用、实际输出、版本及源码/产物哈希。原始本地报告在 `.property-lab/dotenv-dsh-fixed-20261025/`。旧的 [result-summary.json](result-summary.json) 与原 DSH 失败摘要保留原值，描述的是修复前提交 `ba5d11b` 的适配器及导出器；其中旧源码哈希不应拿来校验修复后文件。

## 被测版本与性质依据

- [PyPI 1.2.4](https://pypi.org/project/python-dotenv/1.2.4/)：在执行日核对为最新稳定版；发布时间为 2026-10-01。隔离虚拟环境安装固定版本，未修改上游代码。
- [v1.2.4 README 的文件格式说明](https://github.com/theskumar/python-dotenv/blob/v1.2.4/README.md#file-format)：支持带引号的值、单引号内的反斜杠及引号转义、多行值。
- [上游 test_set_key_round_trips](https://github.com/theskumar/python-dotenv/blob/a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7/tests/test_main.py#L60)：已有写入/读取相等以及后续 sentinel 不被吞掉的测试。本案例将这些样例扩展为字符组合的属性搜索。
- [set_key 与 dotenv_values 源码](https://github.com/theskumar/python-dotenv/blob/a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7/src/dotenv/main.py#L193)：使用真正的公共 API，明确设置 `quote_mode="always"`、UTF-8 和 `interpolate=False`。
- [1.2.3 变更记录](https://github.com/theskumar/python-dotenv/blob/v1.2.4/CHANGELOG.md#123---2026-08-16)：反斜杠写入/读取的旧问题已修复。本案例没有将旧版本问题当成最新版本的新发现。

性质是 `read_value(write_value(s)) == s`。`write_value` 在自动清理的临时目录里通过 `set_key` 写入 `VALUE`，再写入固定的 `SENTINEL`；返回真实文件文本。`read_value` 用 `dotenv_values(stream=StringIO(...), interpolate=False)` 解析，并检查 sentinel 和键集合。适配器不自行实现转义/反转义，不修复或截断被测值。

输入长度为 0–120，明确字符表包含 ASCII 字母数字、路径及 dotenv 常见标点、单/双引号、反斜杠、美元符号及花括号、空格、LF、TAB，以及 `é`、`中`、`🙂`。CR 涉及文本模式的行尾规范化，NUL 不适合普通环境变量值，孤立代理码位不能正常 UTF-8 编码，因此这些均不在本次输入域。这里也不测试任意键名、其他 quote mode、shell `source`、变量展开、权限或符号链接行为；没有把这些未测范围宣称为无 bug。

关闭展开非常关键：`${VALUE}` 等内容在本性质中是字面字符串；默认 POSIX 展开改变它们是预期功能，不能作为往返 bug。所有文件都是合成数据，适配器始终给出明确文件路径或 stream，不调用 `find_dotenv` / `load_dotenv`，不读取用户已有 `.env`，不修改进程环境。临时目录位于本案例目录，通过上下文管理器自动清理；本节记录的 CLI 验证正常完成。若其他执行环境拒绝清理，应单独记录为环境问题，不据此认定上游 bug。案例 `.gitignore` 排除了这些运行目录。

## 首次独立 CLI 结果（修复前，历史记录）

| 项目 | 记录 |
| --- | --- |
| Python / 系统 | CPython 3.13.15 / Windows 11 |
| python-dotenv / Hypothesis / Property Lab | 1.2.4 / 6.170.9 / 0.1.0 |
| 上游 tag / commit | `v1.2.4` / `a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7` |
| 开始时间 UTC | `2026-10-25T08:53:50.240325+00:00` |
| 结束时间 UTC | `2026-10-25T08:53:57.829854+00:00` |
| Seed / max_examples / evaluations | `20261025` / `2500` / `2500` |
| 引擎耗时 / 超时上限 | `6.428105 s` / `180 s` |
| CLI 结果 / 退出码 | `no_counterexample` / `0` |
| 导出测试复跑 | 1 项属性测试通过，设置 `max_examples=2500` |
| 独立边界控制 | 14 个直接调用文件 API 的样例通过 |

独立边界控制绕过适配器，用 `dotenv_values(path, interpolate=False)` 直接读取写入文件，涵盖末尾反斜杠、反斜杠加引号、正则表达式文本、字面 `\\n`、实际 LF、多行、TAB、变量语法、空串和 Unicode。`15 passed` 是 pytest 测试项数，不是属性评估次数。没有反例，所以未导出 `test_regression.py`，也没有可向当前 main 追查的候选问题；本次未另外执行 main。

## 文件与证据

- [adapter.py](adapter.py)：薄适配器。
- [roundtrip.json](roundtrip.json)：包含性质依据和输入域的规格。
- [requirements.txt](requirements.txt)：本次目标包和测试依赖的固定版本；执行器从本仓库安装。
- [fixture_directory.py](fixture_directory.py)：只管理本案例合成目录的权限继承与严格清理。
- [probe_permissions.py](probe_permissions.py)：记录受限令牌、目录 ACL 和真实文件操作结果。
- [test_property_dsh_exported.py](test_property_dsh_exported.py)：修复后 DSH 本轮生成并执行的测试，原字节复制。
- [test_property_exported.py](test_property_exported.py)：首次 CLI 的历史导出，原样保留；DSH 中请使用上面的新导出。
- [test_direct_examples.py](test_direct_examples.py)：14 个明确边界值的独立文件 API 控制。
- [result-summary.json](result-summary.json)：首次 CLI 历史摘录；[dsh-permission-fix.json](dsh-permission-fix.json)：修复后的 DSH 证据。两者均保留真实时间/计数、版本、源码和产物 SHA256。

摘要明确标注了路径变换：原机器的项目路径改为仓库相对路径，输出和解释器改为 `<WORK>` / `<ISOLATED_VENV>` 占位符。它不是未修改的原始报告，不能冒充原始证据文件。原始 `report.json`、HTML/Markdown、worker/process 日志、安装日志、pytest 日志与完整本机 provenance 保留在本次工作目录的 `work/real-projects/dotenv/`，不纳入可移植案例。

执行器原报告的 `source_files` 仅识别到适配器；因此摘要另外记录了**实际安装并执行的上游** `dotenv/main.py`、`dotenv/parser.py`、`dotenv/version.py` 的 SHA256。这些哈希不是包装层哈希，也不是从另一个 checkout 代取。已核对的官方源码 checkout 用于阅读文档、源码和测试，其 commit 独立记录。摘要同时保存原始报告、导出测试及 pytest 日志哈希，便于核对本地证据。执行器的 `spec_sha256` 是规范化规格对象的哈希，`additional_artifact_hashes.roundtrip.json` 则是规格文件原始字节的哈希，二者口径不同。

## 复现

从仓库根目录建立一个新的隔离环境。PowerShell 示例：

```powershell
python -m venv case-studies/dotenv/.venv
& ./case-studies/dotenv/.venv/Scripts/python.exe -m pip install -r case-studies/dotenv/requirements.txt -e .
& ./case-studies/dotenv/.venv/Scripts/python.exe case-studies/dotenv/probe_permissions.py
& ./case-studies/dotenv/.venv/Scripts/python.exe -m dsh_property_lab run case-studies/dotenv/roundtrip.json --project case-studies/dotenv --seed 20261025 --max-examples 2500 --timeout 180 --output .property-lab/dotenv-reproduction

Push-Location case-studies/dotenv
& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider test_property_dsh_exported.py test_direct_examples.py
Pop-Location
```

输出目录必须不存在或为空；再次运行时更换 `--output`。要验证 DSH 权限，需在 DSH 的 `pwsh` 工具中执行这些命令，并确认探针的 `restricted_token=true`；普通命令行的 `false` 不能作为 DSH 受限环境证明。macOS/Linux 使用 `.venv/bin/python`，探针的 Windows 令牌字段为 `null`；本次实际验证平台只有 Windows。案例只验证声明输入域内的公开接口行为，搜索预算耗尽不建立完整正确性。
