# boltons：有序去重等价性

2026-10-25 实际测试 PyPI 最新稳定版 **boltons 26.2.0**（2026-09-07 发布）。两次真实 `dsh-property-lab run`，种子分别为 `20261025`、`20261026`，各配置 `max_examples=3000`、超时 180 秒，报告均记录 **3000 次评估、`no_counterexample`**。本案例没有确认上游 bug，也不证明该函数或整个项目不存在缺陷。

## 契约和输入域

[`unique`](https://boltons.readthedocs.io/en/latest/iterutils.html#boltons.iterutils.unique) 返回去重列表并保持首次出现顺序。版本依据是 [PyPI 26.2.0](https://pypi.org/project/boltons/26.2.0/)，具体契约再次核对了 [发布提交的源码及 docstring](https://github.com/mahmoud/boltons/blob/4332b35a278d694f30c99881faa61cde695c7a96/boltons/iterutils.py#L820-L866)，避免仅依赖会变动的 `latest` 文档。

测试直接调用已安装的 `boltons.iterutils.unique`；[boltons_adapter.py](boltons_adapter.py) 只提供独立参考实现：逐项与已输出元素比较，相等则跳过，否则追加。参考实现没有调用 boltons，也没有使用上游的集合去重算法。

[规格](unique-equivalence.json) 限定输入为长度 0–80 的整数列表，同时混合 `-8..8` 密集范围和不指定数值上下界的 Python 整数，以覆盖重复元素和较大整数。允许任意顺序；不覆盖浮点数、NaN、不可哈希元素、自定义相等运算或 `key` 参数。

## 实际结果与证据

| 运行 | 种子 | 搜索设置 | 实际评估 | 状态 |
| --- | --- | --- | --- | --- |
| 第一次 | 20261025 | 3000 | 3000 | `no_counterexample` |
| 第二次 | 20261026 | 3000 | 3000 | `no_counterexample` |

环境为 Windows 11、CPython 3.13.15、Hypothesis 6.170.9、dsh-property-lab 0.1.0。[summary.json](summary.json) 从原始报告提取运行时间、结果与 SHA-256，移除了本机绝对路径，未改写结果。两个种子的输入可能重叠，不能把 6000 次评估称为 6000 个不同输入。

已检查[上游测试文件](https://github.com/mahmoud/boltons/blob/4332b35a278d694f30c99881faa61cde695c7a96/tests/test_iterutils.py)；其中没有直接测试 `unique` 的用例。本次实际执行发布版本 `unique` 和 `unique_iter` docstring 中的 6 条 doctest，全部通过。安装的 `iterutils.py` 与发布提交下载文件逐字节一致，SHA-256 为 `7fb67f49dc1d895051549b523c2e21161e3c1f4e21590fa7fd09039386d08510`。还实际运行了第一次报告导出的 `test_property.py`，结果为 `1 passed`。这不是完整上游测试套件验证。

原始报告、导出测试、执行日志、安装日志、依赖冻结文件及上游源码核对记录保存在本任务工作目录的 `work/real-projects/boltons/`。仓库只收录可移植的规格、参考实现、依赖与摘要，不包含虚拟环境和带本机路径的原始报告。

## 复现

在 dsh-property-lab 仓库根目录使用 Python 3.10+；如需尽量匹配已记录环境，使用 Python 3.13.15。以下 PowerShell 命令创建独立环境和两份新报告：

```powershell
python -m venv case-studies/boltons/.venv
& ./case-studies/boltons/.venv/Scripts/python.exe -m pip install -r case-studies/boltons/requirements.txt
& ./case-studies/boltons/.venv/Scripts/python.exe -m pip install -e .
& ./case-studies/boltons/.venv/Scripts/python.exe -m dsh_property_lab run case-studies/boltons/unique-equivalence.json --project case-studies/boltons --seed 20261025 --max-examples 3000 --timeout 180 --output .property-lab/boltons-20261025
& ./case-studies/boltons/.venv/Scripts/python.exe -m dsh_property_lab run case-studies/boltons/unique-equivalence.json --project case-studies/boltons --seed 20261026 --max-examples 3000 --timeout 180 --output .property-lab/boltons-20261026
$env:PROPERTY_LAB_PROJECT = (Resolve-Path case-studies/boltons).Path
& ./case-studies/boltons/.venv/Scripts/python.exe -m pytest .property-lab/boltons-20261025/test_property.py -q
```

报告输出目录必须为空或不存在，重复运行时请换新目录。macOS/Linux 可用 `python3 -m venv`，并把解释器路径替换为 `case-studies/boltons/.venv/bin/python`。这里只记录已经执行的本地检查，不宣称 DSH 模型参与了这些两次 CLI 运行；若另有 DSH 验证，应单独记录。
