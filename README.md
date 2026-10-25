# dsh-property-lab

[English](README.en.md)

让 DeepSeek Harness（DSH）用 **Python + Hypothesis** 找到边界输入，把失败情况缩减成反例，并保存可重复运行的测试。

DSH 负责阅读代码、提出有依据的性质和输入域；本项目的本地执行器负责实际运行、缩减和导出证据。CLI 本身不调用模型，也不需要额外的模型 API key。

```text
源码 / 文档 / 现有测试
        ↓ DSH 提出性质及依据
      JSON 规格
        ↓ Hypothesis 生成输入、寻找并缩减失败
  反例 + 运行报告 + 回归测试
```

## 第一版支持什么

| 性质 | 要验证的规则 | 适用例子 |
| --- | --- | --- |
| 往返 `roundtrip` | `inverse(function(x)) == x` | 编码与解码、序列化与反序列化 |
| 幂等 `idempotence` | `function(function(x)) == function(x)` | 规范化、格式化 |
| 等价 `equivalence` | `function(x) == reference(x)` | 重构、优化、替代实现 |

支持同步、单个位置参数的 Python 函数。输入策略包括字符串、整数、布尔值、列表、固定 JSON 值和策略组合。性质规格必须包含依据 `rationale` 和有效输入域 `domain`，避免把模型猜测直接当作程序契约。

## 真实开源项目验证

2026-10-25，在 Windows 11 / Python 3.13.15 / Hypothesis 6.170.9 上，实际测试了三个项目当日的 PyPI 最新稳定版。结果是：**在 toml 中复现两个实现缺陷；python-dotenv 和 boltons 在所测输入域及预算内未找到反例。** 这些案例调用未修改的第三方包；本仓库只提供薄适配器、独立参考实现和测试规格。

| 项目与固定版本 | 实际检查的规则 | 首轮 CLI 评估次数 | 结果与证据 |
| --- | --- | --- | --- |
| [toml 0.10.2](https://pypi.org/project/toml/0.10.2/) | 字符串、字符串列表的序列化/解析往返 | 29 / 32 | U+001F 触发 `IndexError`；`['"']` 往返变为 `['']`。各稳定复现三次。[过程与复现](case-studies/toml/README.md) |
| [python-dotenv 1.2.4](https://pypi.org/project/python-dotenv/1.2.4/) | 带引号值写入/读取，关闭变量展开并检查后续键 | 2,500 | `no_counterexample`；导出属性测试及 14 个独立边界样例共 15 项通过。[过程与复现](case-studies/dotenv/README.md) |
| [boltons 26.2.0](https://pypi.org/project/boltons/26.2.0/) | `unique` 与独立保序去重实现等价 | 3,000 | `no_counterexample`；第二个 seed 再评估 3,000 次也未发现差异。[过程与复现](case-studies/boltons/README.md) |

toml 的控制字符问题对应已公开的 [issue #246](https://github.com/uiri/toml/issues/246)，属于**已知问题复现**。数组引号问题经独立复核支持定性为实现缺陷，但没有确认首次发现。0.10.2 虽是该包最新发布版，发布时间是 2020 年；本次也对获取的上游 HEAD 直接复现了这两个输入。没有向上游提交 issue 或 PR。

### 实际验证流程

1. 核对官方版本、文档、源码及现有测试，先确定输入域与性质；每个目标使用独立虚拟环境。
2. 编写可审查的 JSON 规格和薄适配器，固定版本及 seed `20261025`，执行真正的 `dsh-property-lab run`。toml 每条搜索预算为 2,000，dotenv 为 2,500，boltons 为 3,000；表中记录实际评估数。
3. 对 toml 反例执行独立 `replay` 与导出的回归测试：两项回归测试均按预期失败；再绕过适配器调用公开 API，并用标准库 `tomllib` 交叉检查。
4. 让真实 DSH `0.1.2-rc.1` / `deepseek-flash` 加载技能，用准备好的独立环境重跑四份规格，再核对持久化工具调用与报告。[DSH 调用证据](case-studies/dsh-verification.json)
5. 保存版本、命令、输入域、真实观测、时间与源码/报告 SHA-256；仓库中的摘要明确标注了本机路径的替换方式。

**DSH 复跑有一项环境限制：** toml 两条结果一致，boltons 仍未找到反例；dotenv 的临时目录清理触发 `PermissionError / WinError 5`，该轮状态是 `inconclusive`、退出码 2，不能算 dotenv 缺陷，也不能算 DSH 验证通过。上表 2,500 次是独立 CLI 的成功运行。原始记录保留，未关闭沙箱或忽略清理错误来改变结论。

可独立复现的 toml 示例（安装案例的固定依赖后）：

```python
import toml
import tomllib  # Python 3.11+

original = {"value": ['"']}
encoded = toml.dumps(original)
print(toml.loads(encoded))     # {'value': ['']}
print(tomllib.loads(encoded))  # {'value': ['"']}
```

每个案例目录都提供安装/运行命令、规格与可移植证据。未发现反例不等于证明正确；不同轮次的输入可能重叠，评估次数不能直接当作独立输入总数。核心测试、案例测试、第三方缺陷复现和 DSH 环境问题分别记录，不汇总成一个“全通过”数字。

## 本地安装

需要 Python **3.10 或更高版本**。建议在项目独立的虚拟环境运行，目标代码的依赖也需安装在该环境中。

Windows PowerShell，在仓库根目录执行：

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe -m dsh_property_lab doctor
```

macOS / Linux：

```sh
sh scripts/setup.sh
.venv/bin/python -m dsh_property_lab doctor
```

也可以使用自己已有的 Python 环境：

```sh
python -m pip install -e ".[dev]"
python -m dsh_property_lab doctor
```

## 接入桌面 DSH

使用刚才安装好的解释器，在仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m dsh_property_lab install-dsh
```

安装器将技能放入 DSH 的用户技能目录，生成指向此项目解释器的启动入口。它不修改 DSH profile。自定义 DSH home 时使用 `--dsh-home PATH`。移动或删除项目、重建虚拟环境后，需要重新运行安装命令。

然后在桌面 DSH 的新对话里输入：

> 使用 dsh-property-lab，检查这个 Python 项目的编码函数。先从文档和测试说明往返性质及输入域，再生成规格并运行；保存反例和回归测试，不修改业务代码。

兼容目标包括桌面 DSH `0.1.2-rc.1` 的本地技能加载机制。若技能列表尚未刷新，重新打开一个对话。运行 `doctor` 可以检查当前解释器与依赖；它不会证明模型已正确使用技能。

## 跑通自带演示

```powershell
.\.venv\Scripts\python.exe -m dsh_property_lab demo
```

演示包含三组**故意设置缺陷的教学函数及修复版**：

| 示例 | 缺陷 | 便于理解的失败输入 |
| --- | --- | --- |
| 表单编码往返 | 错把字面量 `+` 当作不必转义的字符 | `"+"` 解码后变成空格 |
| 空格规范化幂等 | 只执行一次双空格替换 | 三个连续空格 |
| 保序去重等价 | 去重时排序，改变了首次出现顺序 | `[0, -1]` |

上表是可说明缺陷的输入；实际运行找到并缩减的反例记录在报告里，不保证与表中逐字相同。这些结果不能作为“发现了第三方项目漏洞”的宣传。

单独运行一份规格：

```powershell
.\.venv\Scripts\python.exe -m dsh_property_lab run examples/roundtrip-buggy.json --project . --seed 2026 --max-examples 300 --timeout 60
```

CLI 输出实际报告目录。默认运行结果写入 `.property-lab/runs/`，该目录已被 Git 忽略。用 `--output DIR` 指定其他目录；指定目录必须不存在或为空，以免覆盖已有证据。

## 检查你自己的代码

假设项目中有 `codec.py`，提供 `encode(value)` 和 `decode(value)`。创建 `encoding-property.json`：

```json
{
  "version": 1,
  "name": "encoding-roundtrip",
  "kind": "roundtrip",
  "function": "codec:encode",
  "inverse": "codec:decode",
  "strategy": {
    "type": "text",
    "alphabet": "ab09 +%",
    "min_size": 0,
    "max_size": 40
  },
  "rationale": "项目文档约定 decode(encode(value)) 恢复原文，包括空格及加号。",
  "domain": "长度 0 至 40、字符来自 ab09 +% 的字符串。"
}
```

从任意目录调用已安装执行器，指定目标项目：

```powershell
python -m dsh_property_lab run encoding-property.json --project "C:\path\to\your-project"
```

`function`、`inverse` 和 `reference` 使用 `Python模块:函数名`。项目根目录会加入目标进程的模块搜索路径；对于 `src` 布局，请先把目标项目安装进同一虚拟环境。第一版不自动重写函数签名、安装目标依赖或修改业务代码。

## 结果与复现

每次运行会保存 `report.json`、`report.md` 和 `report.html`。有效规格会导出 `test_property.py`；确认可重复的反例还会导出 `test_regression.py`。报告保留规格、seed、版本、源码文件哈希和观测结果；目标输出及进程日志保存在 `worker.log`、`process.log`，没有输出时日志可以为空。

复查保存的反例：

```powershell
python -m dsh_property_lab replay "PATH\TO\report.json" --project "C:\path\to\your-project"
```

运行导出的测试时，使用带有目标依赖的环境，先切换到被测项目根目录，或将环境变量 `PROPERTY_LAB_PROJECT` 设为该目录。再用报告中的实际文件路径执行：

```sh
python -m pytest PATH/TO/test_regression.py
python -m pytest PATH/TO/test_property.py
```

反例测试在有缺陷的实现上应失败；业务代码修复后应通过。修改后的目标代码与首次运行不是同一个版本时，复现结果也可能不同。

| 运行状态 | 含义 | `run` 退出码 |
| --- | --- | --- |
| `counterexample` | 找到并复查了违反所述性质的输入，需要进一步判断原因 | `1` |
| `no_counterexample` | 在本次搜索预算内没有找到反例，不是正确性证明 | `0` |
| `inconclusive` / `error` | 输入域、环境、超时、非确定性等问题阻碍可靠结论 | `2` |

生成与缩减可能反复调用目标函数，实际调用次数可能超过 `--max-examples`；该参数是 Hypothesis 搜索设置，不是总调用次数的硬上限。`--timeout` 提供单次子进程运行的时间上限。

## 范围和限制

- 只对可信的本地项目运行。导入和测试 Python 模块会执行其代码；子进程和超时机制**不是安全沙箱**。
- 先核对性质及输入域。失败可能来自性质错误、输入不符合业务约束或实现缺陷；工具不自动把所有失败认定为 bug。
- 目标应可重复运行，并避免网络、文件写入和其他外部副作用。随机状态、时间和全局状态会影响结果。
- Hypothesis 会缩减输入，但缩减结果不保证数学意义上的全局最小值。
- 本版本不覆盖异步函数、多参数函数、浏览器端到端测试和任意 Python 对象输入。
- 报告可能包含输入和目标代码的输出，不要将私有数据直接提交到公开仓库。

## 开发

```sh
python -m pip install -e ".[dev]"
python -m pytest
```

仓库包含可用于 GitHub Actions 的测试工作流。将此目录发布为自己的 GitHub 仓库即可；项目未绑定任何预设的远程地址或账号。

本次实际执行过的测试、兼容性与尚未验证的范围见 [VALIDATION.md](VALIDATION.md)。

## 许可与致谢

本项目的代码和技能说明为独立编写，采用 [MIT](LICENSE) 许可。测试引擎使用 [Hypothesis](https://hypothesis.readthedocs.io/)；技能方向受到 [Trail of Bits 的 property-based-testing 技能](https://github.com/trailofbits/skills/tree/main/plugins/property-based-testing) 启发，但未复制其技能文本或脚本。该上游项目采用自己的 CC-BY-SA-4.0 许可，不受本项目 MIT 许可覆盖。
