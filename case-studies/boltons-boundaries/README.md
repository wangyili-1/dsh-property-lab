# boltons：正数分割上限处的连续分隔符

2026-10-25 对未经修改的 [boltons 26.2.0](https://pypi.org/project/boltons/26.2.0/) 实际运行 `dsh-property-lab`，发现 `split(..., sep=None, maxsplit=1)` 在达到上限时没有完整消费第一处分隔段。两种种子都缩减到 `[0, None, None]`：返回 `[[0], [None]]`，文档规定的分组合并语义应得到 `[[0]]`。

这是已复现的**文档约定与实现行为不一致**。本案例不声称维护者已确认，也不声称首次发现；没有提交上游 issue 或 PR。源码检查先于性质设计，本次不是盲测。未修改原有 `unique` 无反例案例或 boltons 代码。

## 契约、输入域与参考实现

[官方文档](https://boltons.readthedocs.io/en/latest/iterutils.html#boltons.iterutils.split_iter) 将 `split` 定义为面向一般可迭代对象的 `str.split`，并明确说明 `sep=None` 会合并连续分隔符。已核对 [26.2.0 发布提交源码及 docstring](https://github.com/mahmoud/boltons/blob/4332b35a278d694f30c99881faa61cde695c7a96/boltons/iterutils.py#L109-L198)，而非只依赖会更新的 latest 文档。[Python `str.split`](https://docs.python.org/3.13/library/stdtypes.html#str.split) 给出独立的分组及分割上限语义。

[规格](split-grouped-limit.json) 限定长度 0–60 的列表，元素为 `-9..9` 的整数或 `None`；固定 `sep=None, maxsplit=1`。负整数只是普通列表元素，不是分割次数。空列表及连续 `None` 均在一般可迭代输入和文档示例的范围内。排除布尔值、自定义相等运算、其他分隔符、负分割次数，以及 `maxsplit=0`。[上游零上限测试](https://github.com/mahmoud/boltons/blob/4332b35a278d694f30c99881faa61cde695c7a96/tests/test_iterutils.py#L28-L33) 明确规定零上限原样返回，不应套用 Python 字符串的零上限行为制造反例。

[适配器](boltons_boundaries_adapter.py) 的目标函数仅固定参数后直接调用公开 `split` API。独立参考实现把 `-9..9` 一一编码成 `A..S`、把 `None` 编码为空格，调用标准库 `str.split(None, 1)` 后逆编码；非空白字符与整数一一对应，没有信息损失。

本性质要求完整消费第一处分隔段，并**保留未分割余段内部的后续分隔符**：

| 输入 | 实际结果 | 文档语义的参考结果 |
| --- | --- | --- |
| `[0, None, None]` | `[[0], [None]]` | `[[0]]` |
| `[0, None, None, 1]` | `[[0], [None, 1]]` | `[[0], [1]]` |
| `[0, None, 1, None, None]` | `[[0], [1, None, None]]` | 相同 |

源码在遇到第一个分隔符后增加计数；下一轮一旦计数到达上限，就关闭分隔符判断。因此同一连续分隔段中的第二个 `None` 被放进余段。该解释对应上述差异，不要求所有输出都不得含 `None`。

## 实际执行与证据

环境为 Windows 11、CPython 3.13.15、Hypothesis 6.170.9、dsh-property-lab 0.1.0、pytest 9.1.1。运行结果由 [summary.json](summary.json) 从原始报告选取并移除本机路径，同时保留原始文件 SHA-256。

| 搜索 | 种子 | 配置上限 | 实际评估 | 结果 |
| --- | --- | --- | --- | --- |
| 原始字符串探查 | 20261025 | 1500 | 14 | 缩为 `"a  "`，多出空格余段 |
| 整数/None 主规格 | 20261025 | 2000 | 44 | `[0, None, None]` |
| 整数/None 主规格 | 20261026 | 2000 | 29 | `[0, None, None]` |
| 精确 replay | 20261025 | 不适用 | 1 | 同一反例再次复现 |

每次主搜索报告另记录三次一致复现。[导出的回归测试](test_regression.py) 已实际执行，结果为预期的 `1 failed`，断言正是 `[[0], [None]] != [[0]]`。反例是 Hypothesis 在各次运行中缩减得到的结果，不声称全局最小。评估包括生成与缩减，种子间输入可能重叠，不能将次数相加称为独立覆盖。

[独立验证记录](independent-verification.json) 不导入适配器或 CLI，直接调用公开 API，对九个手工列明预期的边界案例各执行三次。也实际加载并检查了 [上游 HEAD 4e5faa3](https://github.com/mahmoud/boltons/blob/4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d/boltons/iterutils.py)：相关差异同样复现。安装文件、发布提交文件与该 HEAD 的 `iterutils.py` 逐字节一致，SHA-256 都为 `7fb67f49dc1d895051549b523c2e21161e3c1f4e21590fa7fd09039386d08510`。`split` 与 `split_iter` 的六条 docstring 示例通过；这不等于执行完整上游测试套件。

独立复核使用另写的位置扫描参考算法，不使用字符串编码、`str.split` 或 boltons；在元素取自 `[-1, 0, 1, None]`、长度 0–6 的全部 **5,461 个列表**上与当前参考函数比较，得到零差异。[独立参考审查摘要](oracle-audit-summary.json) 保留实际运行时间、源码哈希和原始记录哈希；原始脚本及记录为 `work/counterexamples/boltons/oracle-audit.py` 和 `oracle-audit.json`。这是有限域的参考实现审查，不计作新 CLI 搜索，也不证明完整主规格输入域。

按 `repo:mahmoud/boltons maxsplit` 检索公开 issue/PR，找到已合并的 [#406：零上限处理](https://github.com/mahmoud/boltons/pull/406) 与尚未合并的 [#502：负上限处理](https://github.com/mahmoud/boltons/pull/502)。它们针对不同边界；有限关键词检索不能证明本案例的新颖性。

原始报告、日志、源码快照、下载失败记录、依赖冻结文件及验证脚本保存在任务目录 `work/counterexamples/boltons/`。这里的记录由 Codex 调用真实 CLI 产生；若另有 DSH 模型验证，应单独列出。

## 同次保留的未发现反例探查

以下 [原规格与适配器](exploratory/) 保留了实际执行内容，均为种子 `20261025`、配置上限 1500、实际评估 1500、超时 60 秒，结果均为 `no_counterexample`。三个不同性质的总评估次数不能表示互不重复的输入数，也不证明函数正确。

| 目标 | 性质与输入域 |
| --- | --- |
| `parse_timedelta` | 单一整数秒项，`-100000000..100000000`，解析结果等于该秒数；不假设重复单位相加或无限小数精度 |
| `windowed` | 固定 `size=3, fill=None`，长度 0–80、元素 `-100..100` 的整数列表，等于逐位置切片并补齐的窗口 |
| `Bits` | 长度 0–128 的二进制文本，经 `from_bin(...).as_bin()` 保持内容与位宽；不把按字节补齐当作精确位宽往返 |

另外排除了 `bytes2human` 的舍入损失，以及 `parse_int_list` 文档只承诺正整数这两类不适合据此指认缺陷的假设。

## 复现

从 dsh-property-lab 仓库根目录使用 Python 3.10+，匹配本次环境可使用 Python 3.13.15：

```powershell
python -m venv case-studies/boltons-boundaries/.venv
& ./case-studies/boltons-boundaries/.venv/Scripts/python.exe -m pip install -r case-studies/boltons-boundaries/requirements.txt
& ./case-studies/boltons-boundaries/.venv/Scripts/python.exe -m pip install -e .
& ./case-studies/boltons-boundaries/.venv/Scripts/python.exe -m dsh_property_lab run case-studies/boltons-boundaries/split-grouped-limit.json --project case-studies/boltons-boundaries --seed 20261025 --max-examples 2000 --timeout 60 --output .property-lab/boltons-boundaries-20261025
$env:PROPERTY_LAB_PROJECT = (Resolve-Path case-studies/boltons-boundaries).Path
& ./case-studies/boltons-boundaries/.venv/Scripts/python.exe -m pytest case-studies/boltons-boundaries/test_regression.py -q
```

预期 CLI 返回 `counterexample`、退出码 1，回归测试失败。换新种子或重复运行时使用新的报告目录。三个未发现反例探查可将 `--project` 改为 `case-studies/boltons-boundaries/exploratory`，选择对应 JSON 并使用 `--max-examples 1500`。这些是复现命令，不代表在所有 Python 版本上均已测试。
