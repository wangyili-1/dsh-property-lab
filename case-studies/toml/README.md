# toml：真实字符串序列化与解析缺陷

2026-10-25 测试当日 PyPI 最新稳定版 **toml 0.10.2**，找到并独立复现两个实现缺陷。这个发布版本发布于 2020-11-01；“最新发布版”不表示项目仍活跃维护。控制字符问题属于已有 issue 的复现，双引号数组问题的新颖性未确认。没有修改上游源码，也没有提交 issue 或 PR。

## 性质与依据

[上游 API 文档](https://pypi.org/project/toml/0.10.2/)说明 `dumps` 将字典序列化为对应 TOML，`loads` 将 TOML 解析回字典。[TOML 0.5.0 字符串规则](https://toml.io/en/v0.5.0#string)支持 Unicode 标量值，要求转义双引号、反斜杠及控制字符；同类型字符串数组也合法。已阅读上游 [tests/test_api.py](https://github.com/uiri/toml/blob/65bab7582ce14c55cdeec2244c65ea23039c9e6f/tests/test_api.py) 中的往返测试。

`toml_adapter.py` 只执行 `toml.dumps({"value": value})` 和 `toml.loads(document)["value"]`，没有实现或修补编码算法。两个规格分别生成长度 0–64 的 Unicode 字符串，以及长度 0–8、元素长度 0–32 的字符串列表。Hypothesis 默认字符域排除孤立代理码点；没有混合类型数组、bytes 或自定义对象。

## 实际结果

环境：Windows 11、CPython 3.13.15、Hypothesis 6.170.9、Property Lab 0.1.0。两个规格均使用 seed `20261025`、`max_examples=2000`、timeout 120 秒；发现失败后缩减并停止，因此不能写成“各跑满 2000 例”。

| 规格 | 实际评估次数 | 缩减反例 | 实际行为 | 状态 / 退出码 |
| --- | --- | --- | --- | --- |
| [字符串](string-roundtrip.json) | 29 | `"\u001f"`，一个 U+001F 字符 | `toml.dumps` 抛 `IndexError: list index out of range` | `counterexample` / 1 |
| [字符串列表](string-list-roundtrip.json) | 32 | `['"']`，列表里只有一个双引号字符 | 往返结果为 `['']`，内容丢失 | `counterexample` / 1 |

两项均在运行器内部稳定复现三次，随后独立 `replay` 仍报告 `counterexample`。导出的两个回归测试实际执行得到 **2 failed**：它们断言正确的往返行为，在未修复的目标版本上失败正是预期证据，不能将其标为上游测试通过。

## 独立复核与定性

[reproduce.py](reproduce.py) 不导入 Property Lab 或适配器，直接调用第三方公开 API，并用 Python 标准库 `tomllib` 作第二个解析器（该辅助脚本要求 Python 3.11+）。

```python
import toml
import tomllib

toml.dumps({"value": "\x1f"})  # IndexError

original = {"value": ['"']}
encoded = toml.dumps(original)
print(toml.loads(encoded))      # {'value': ['']}
print(tomllib.loads(encoded))   # {'value': ['"']}
```

对于 U+001F，手写合法的 `value = "\u001f"` 文档可被这两个解析器正确读取，所以输入值有合法 TOML 表示，问题在编码路径。该行为对应已公开的 [uiri/toml #246](https://github.com/uiri/toml/issues/246)，本项目记录为**已知缺陷的自动复现**。

对于双引号数组，同一份上游编码器输出能被 `tomllib` 正确还原，但 `toml.loads` 丢失内容，支持将其定性为解码实现缺陷。没有确认它是首次发现，也没有声称维护者确认过本次具体反例。

另对执行日获取的上游 HEAD `65bab7582ce14c55cdeec2244c65ea23039c9e6f`（提交日期 2023-10-11）直接运行同一独立脚本，两种行为仍可复现。这是两个具体输入的 HEAD 复核，不是对 HEAD 完整重跑属性搜索或完整测试套件。

## 可复现步骤

在本仓库根目录使用 PowerShell：

```powershell
python -m venv case-studies/toml/.venv
& ./case-studies/toml/.venv/Scripts/python.exe -m pip install -r case-studies/toml/requirements.txt -e .
& ./case-studies/toml/.venv/Scripts/python.exe -m dsh_property_lab run case-studies/toml/string-roundtrip.json --project case-studies/toml --seed 20261025 --max-examples 2000 --timeout 120 --output .property-lab/toml-string-reproduction
& ./case-studies/toml/.venv/Scripts/python.exe -m dsh_property_lab run case-studies/toml/string-list-roundtrip.json --project case-studies/toml --seed 20261025 --max-examples 2000 --timeout 120 --output .property-lab/toml-list-reproduction
& ./case-studies/toml/.venv/Scripts/python.exe case-studies/toml/reproduce.py

$env:PROPERTY_LAB_PROJECT = (Resolve-Path case-studies/toml).Path
& ./case-studies/toml/.venv/Scripts/python.exe -m pytest -q case-studies/toml/test_regression_string.py case-studies/toml/test_regression_string_list.py
```

两个 `run` 和最后的 pytest 在未修复版本上预期退出 1；独立诊断脚本只输出观测，不用退出 0 表示目标正确。输出目录必须为空或不存在。macOS/Linux 将解释器换为 `.venv/bin/python`；本次实际执行环境只有 Windows。

## 证据

[summary.json](summary.json) 保留真实状态、反例、三次复现记录、时间、计数、raw report 哈希、实际安装的 `encoder.py` / `decoder.py` 哈希及 HEAD 独立复核结果。它是明确标注的可移植摘录：个人绝对路径被仓库相对路径、`<WORK>` 和 `<ISOLATED_VENV>` 替换，原始报告结果没有重写。自动生成的四个属性/回归测试按原字节复制。

原始报告、日志、未修改的上游 checkout 和独立复核 JSON 留在本次任务的 `work/real-projects/toml/`。真正 DSH 模型的后续同规格复跑另见 [DSH 证据](../dsh-verification.json)，不要把 CLI 和模型调用记录混为一轮。
