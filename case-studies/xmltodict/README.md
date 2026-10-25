# xmltodict：XML 注释内容被错误转义

2026-10-25 在 Windows 11 / Python 3.13.15 上，用真实 `dsh-property-lab` CLI 检查 **xmltodict 1.0.4**。该版本发布于 2026-02-22，是当日 [PyPI 最新稳定版](https://pypi.org/project/xmltodict/)。CLI 将单注释往返反例缩减到 **`"<"`**：解析回来得到字面量 **`"&lt;"`**。

这是**已知实现缺陷的独立复现**。后续核对发现，上游已有仍开放的 [PR #423](https://github.com/martinblech/xmltodict/pull/423)，创建于 2026-08-02，修复相同的注释转义问题。本案例不宣称首次发现，也未向上游发消息、提交 issue 或 PR。

| 实际检查 | 预算 / 实际评估 | 结果 |
| --- | --- | --- |
| 单个元素内注释内容往返 | 3,000 / 19 | `"<"` → `"&lt;"`；CLI 内复现三次 |
| 同字符域的普通文本节点往返 | 3,000 / 3,000 | `no_counterexample` |
| 独立 CLI `replay` | 固定反例 / 1 | 再次稳定复现 |
| CLI 导出的回归测试 | 1 项 | 按预期失败，断言差异为 `('&lt;', '<')` |
| CLI 导出的文本属性测试 | 1 项 | 通过 |
| 下载的上游两个测试模块 | 119 项 | 全部通过；不冒称整个上游测试套件 |

`evaluations` 包括搜索和缩减时的性质评估，不是独立输入数。未找到文本反例只说明本轮预算与输入域中的结果，不证明完全正确。

## 性质依据与输入域

这条性质由源码和现有测试引导，并非盲测。`unparse` 确实具有专门的注释输出分支；[v1.0.4 的测试](https://github.com/martinblech/xmltodict/blob/v1.0.4/tests/test_dicttoxml.py) 中，`test_unparse_with_element_comment` 直接验证 `#comment` 输出，`test_comment_roundtrip_limited` 则执行 `parse → unparse → parse` 并断言元素内注释内容保留。因此，依据不只是解析器的 `process_comments` 参数。

规格生成长度 1–64 的注释，字符域包含字母、数字、空白、部分 Unicode 字符及 XML 注释允许的 `&<>`。固定一个根元素和一个注释；没有混合文本、子元素、属性、命名空间或多个顶层注释。排除连字符以保证没有 `--` 或末尾 `-`，排除 CR、非法 XML 控制字符、代理码点与空注释，并明确使用 `process_comments=True, strip_whitespace=False`。

[XML 1.0 第 2.4、2.5 节](https://www.w3.org/TR/xml/#sec-comments)允许注释中出现字面量尖括号和 `&`；注释不会把 `&lt;` 解释成 `<`。因此，这不属于 CR 正规化、默认去空白或文档说明的注释顺序限制。

## 独立公开 API 复现

```python
import xmltodict

original = "<root><!--<--></root>"
parsed = xmltodict.parse(original, process_comments=True, strip_whitespace=False)
encoded = xmltodict.unparse(parsed)
again = xmltodict.parse(encoded, process_comments=True, strip_whitespace=False)
print(parsed)   # {'root': {'#comment': '<'}}
print(encoded)  # ... <root><!--&lt;--></root>
print(again)    # {'root': {'#comment': '&lt;'}}
```

[reproduce.py](reproduce.py) 不导入适配器或执行器：它用标准库 `xml.dom.minidom` 创建合法原始 XML，调用 xmltodict 公开 API，并用两种解析器分别读回。`<`、`>`、`&` 和组合注释均发生内容变化；普通文本、空白和 Unicode 对照符合所述规则。完整真实输出在 [independent-reproduction.json](independent-reproduction.json)。

安装包的 `xmltodict.py` 与官方 v1.0.4 源文件 SHA-256 完全一致：`701d42ae7298bbdf154163aed261e4f0fd3cc6c803748ec52f312a5bc402c46e`。[源码 `_XMLGenerator.comment`](https://github.com/martinblech/xmltodict/blob/v1.0.4/xmltodict.py#L553-L556) 在注释语法校验后调用 `escape(text)`，使原本合法的注释内容改变。当前案例没有修改第三方实现。

## 重跑

从仓库根目录，在独立环境中安装本仓库及固定依赖；下面是 Windows PowerShell 命令：

```powershell
python -m venv .venv-xmltodict
$casePython = (Resolve-Path .venv-xmltodict/Scripts/python.exe).Path
& $casePython -m pip install . -r case-studies/xmltodict/requirements.txt
& $casePython -m dsh_property_lab run case-studies/xmltodict/comment-roundtrip.json --project case-studies/xmltodict --seed 20261025 --max-examples 3000 --timeout 120 --output .property-lab/xmltodict-comment
& $casePython -m dsh_property_lab run case-studies/xmltodict/text-roundtrip.json --project case-studies/xmltodict --seed 20261025 --max-examples 3000 --timeout 120 --output .property-lab/xmltodict-text
& $casePython -m dsh_property_lab replay .property-lab/xmltodict-comment/report.json --project case-studies/xmltodict --output .property-lab/xmltodict-replay
& $casePython case-studies/xmltodict/reproduce.py
```

输出目录必须不存在或为空。注释搜索、重放和回归测试的退出码应为 `1`，这表示已复现失败。运行导出测试时，切换到案例目录，或将 `PROPERTY_LAB_PROJECT` 指向案例目录。文本属性测试应通过。

[summary.json](summary.json) 保存可移植报告摘要、固定版本、seed、真实命令、退出码、独立复验结果及原始报告哈希；[source-manifest.json](source-manifest.json) 保存官方文件 URL 和下载哈希；[SHA256SUMS.json](SHA256SUMS.json) 校验本案例交付文件。原始未改写报告和运行日志保存在工作区 `work/counterexamples/serialization/`，摘要对本机路径进行了明确标注的替换。

本目录记录的是本地 CLI/Hypothesis 实验。当前未对未发布的上游 HEAD 作验证，也不把这些 CLI 记录冒充模型内部执行证据。
