# humanize 4.16.0：显式小数位格式化改变整数

2026-10-25 核对 [PyPI](https://pypi.org/project/humanize/4.16.0/)，最新稳定版为 **4.16.0**（2026-06-30 发布）。在 Python 3.13.15 / Hypothesis 6.170.9 的独立虚拟环境中，真实 CLI 找到并缩减了一项整数精度缺陷：

```python
import humanize

n = 9007199254740993  # 2**53 + 1，Python int 可以精确表示
print(humanize.intcomma(n, 0))  # 9,007,199,254,740,992（末位改变）
print(humanize.intcomma(n))     # 9,007,199,254,740,993（默认参数保留原值）
print(humanize.intcomma(12345, 0))  # 12,345（小整数对照）
```

这是当前发布版的可复现实现缺陷；**不宣称首次发现**，没有向上游提交 issue 或 PR。

## 性质、范围与判断

[官方文档](https://humanize.readthedocs.io/en/stable/number/#humanize.number.intcomma)将 `intcomma` 定义为给整数增加千分位分隔符；`ndigits` 控制小数点后的舍入精度。因此，对没有小数部分的精确整数请求 `ndigits=0`，应当保留整数值。发布版测试也包含整数输入配合显式精度的用法。

主规格覆盖整个有符号 64 位整数区间 `[-2**63, 2**63-1]`，固定英文默认区域及 `ndigits=0`。没有使用浮点输入、小数、负精度、自定义区域或几百位超大整数。`adapter.py` 仅传递参数；独立参考实现用十进制字符串分组，不调用 humanize、不转换为浮点，也不使用数值格式化。`reproduce.py` 绕过适配器，另外使用标准库 `Decimal` 格式化和数值比较进行交叉核对。

[发布版源码](https://github.com/python-humanize/humanize/blob/3c577d7650508d52aa2982e930b0e744c343082f/src/humanize/number.py#L170-L175)在显式精度分支使用 `f` 数值格式。Python 对整数采用该格式时先经过浮点表示；超过 `2**53` 后，不是所有整数都能被精确表示。此处要审查的是 humanize 选择了会损失整数精度的路径；并不把 Python 浮点格式自身的既定行为算作 Python 的 bug。

## 实际结果

| 检查 | 结果 |
| --- | --- |
| 主规格，seed `20261025`，预算 3,000 | `counterexample`，实际 146 次评估；缩减为 `9007199254740993` |
| CLI 内部重放 | 连续 3 次相同差异 |
| 另起进程执行 `replay` | 3 次均复现，退出码 1 |
| 同域默认 `ndigits=None` 对照 | 3,000 次评估，`no_counterexample` |
| CLI 导出的回归测试 | 预期 `1 failed`，差异为末位 `992` / `993` |
| 导出的默认参数属性测试 | `1 passed` |
| 发布版原有 `intcomma` 测试 | `34 passed, 193 deselected` |
| 直接 API / Decimal 核对 | `0`、`±12345`、`2**53` 正确；`±(2**53+1)` 在显式零小数位时改变值，默认参数正确 |

未发现反例的对照不代表证明整个库正确。评估次数包括生成、缩减等调用，不是互不重复输入数量。本案例只计 **1 项缺陷**；没有把同类精度丢失的 `fractional` 探针另算一项，也没有把上游仍有语义争议的负序数后缀候选算作 bug。

## 已知问题检索

2026-10-25 查询了该官方 GitHub 仓库的 `intcomma precision` 和 `intcomma integer` issue/PR 记录。没有在这些查询结果中确认完全相同的 `signed-64-bit int + ndigits=0` 案例，但检索不构成新颖性证明。

- [PR #392](https://github.com/python-humanize/humanize/pull/392)：默认精度下超出 float 范围的大整数导致溢出，已在发布后合并；该 PR 明确把显式小数位格式化留在范围之外。
- [PR #404](https://github.com/python-humanize/humanize/pull/404)：默认精度下极长整数字符串误报为无穷大。
- [Issue #419](https://github.com/python-humanize/humanize/issues/419)：多个数字函数在超出 float 范围时抛出 `OverflowError`。

本次反例在 float 的有限范围内，表现为静默更改整数末位，没有溢出异常。相关问题已公开，所以报告用“本次发现并复现的缺陷，首次发现未确认”，不使用“全新漏洞”。

## 复现

在仓库根目录创建独立环境（Windows PowerShell；其他平台替换解释器路径）：

```powershell
py -3.13 -m venv .venv-humanize
.\.venv-humanize\Scripts\python.exe -m pip install -e . -r case-studies/humanize/requirements.txt
.\.venv-humanize\Scripts\python.exe -m dsh_property_lab run case-studies/humanize/intcomma-zero-digits.json --project case-studies/humanize --seed 20261025 --max-examples 3000 --timeout 180 --output .property-lab/humanize-zero-digits
.\.venv-humanize\Scripts\python.exe -m dsh_property_lab run case-studies/humanize/intcomma-default-control.json --project case-studies/humanize --seed 20261025 --max-examples 3000 --timeout 180 --output .property-lab/humanize-control
.\.venv-humanize\Scripts\python.exe -m dsh_property_lab replay .property-lab/humanize-zero-digits/report.json --project case-studies/humanize --output .property-lab/humanize-replay
.\.venv-humanize\Scripts\python.exe case-studies/humanize/reproduce.py
$env:PROPERTY_LAB_PROJECT = (Resolve-Path case-studies/humanize).Path
.\.venv-humanize\Scripts\python.exe -m pytest -q case-studies/humanize/test_regression.py
```

输出目录必须不存在或为空。`run` 和 `replay` 找到反例时退出码为 1；最后的回归测试在未修复依赖上应失败。`test_property.py` 是主规格导出的完整属性测试，`test_control.py` 是默认参数的对照。

[summary.json](summary.json)包含真实报告摘要、时间、源文件与报告 SHA-256、直接核对结果及已知问题分类。安装的 `humanize/number.py` 与发布标签下载的源码逐字节一致，SHA-256 为 `dfbd68811a62fa8d824da8aaffc288409ae01351852ec2d301899ea1a6270307`。原始报告、日志、PyPI/GitHub 快照保留在本次工作区 `work/counterexamples/humanize/`，未把本机绝对路径写入可移植的摘要。
