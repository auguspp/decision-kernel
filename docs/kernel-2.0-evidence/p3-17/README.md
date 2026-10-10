# P3-17 固定原件：Smart / Global 回执接线验证

归属 [#508 结果](https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6102969194)。代码基线 `7e770c6704cd3cfdcf496e276bb0bbceb98b106e`。这是一次规划取证的静态数据附件，不是现役测试套件、生产入口、状态库或新执行器。

**27项检查：18项现有行为符合预期，9个案例复现两类未修复协议不兼容。** 最终脚本分别在两个新目录执行，完整输出逐字节相同；不称54项独立测试。原始JSON包括逐项结果、合成调用、保留文件清单、21份源码库存、8个辅助定义/常量的源区间和hash、运行环境及未执行范围。

## 已验证与边界

完整原目标阶段在进程内运行：primary capture/磁盘replay，Relay请求/采集/磁盘replay，Smart native/read_run、原Collector ZIP验证/存取、history/state、可选补充隔离、展示生成及canonical JSON；另跑Global Shibor capture/replay。来源响应、GitHub API/ZIP、时钟、key均为合成；没有真实来源、Git写入、生产恢复、CLI/workflow进程或浏览器JS。

16份目标/基础模块整文件导入，5份旁路依赖只抽取8个未修改定义/常量，范围在输出中列明。空namespace initializer和未被调用的Research导入sentinel不冒充全仓导入闭包。目标validator、ZIP身份、Collector存取和共享预算函数未替换。socket/子进程尝试0；sleep只记录。预装Python3.13.5、Requests2.32.5、BS4 4.14.3、pydantic2.13.5；无安装。

正常Relay v1/v2/v3/reports-only分别5/5/11/7个合成请求。Smart的timeout/connection/request_error/timeout_then_success/nonJSON403/nonJSON429在原磁盘重放被拒；特别是首次超时后成功仍可能被旧字段集合拒读。主源、非空无关lane、已有研究、历史first_seen不因此丢失，调用计数不退回。坏补充ZIP未进入新读取包，但本地producer原件仍在；不可宣传为全体原件均已发布。不同的前一天run16001正常补充可由精确locator恢复，当前run17001缺口继续显式保留。

Global的同类输入在自己的边界转为REQUEST_RECEIPT_UNAVAILABLE、attempts=[]、请求次数null，无raw文件；正常对照AVAILABLE。试验者看到的2/1/1次合成transport调用不是生产未知回执的可回填数字。没有验证Global所有族、Stock/Auction所有读写者、实际线上发生率或经济正确性。

## 无损保管格式

`part-1.b64`至`part-4.b64`按编号串接，得到一个标准base64字符串；解码为gzip，解压为UTF-8 JSON。JSON内仅有README、实际完整脚本和实际完整结果三个文本文件。分块只为这份固定证据保管，项目代码和CI不会读取或执行它们。不要按mtime选择版本，不自动执行解码后的脚本。

| 原件 | bytes | SHA256 |
|---|---:|---|
| gzip | 13969 | `6440a9d006b9fe224bb3aaff0c64fe08b19a5532d0a5b8a54ec988953691bffd` |
| 解压JSON | 56372 | `9ee80a25433135053ffee2ba4bf9281cf93670cc260da19145f150f29d647bf4` |
| check-wiring.py | 27627 | `57aac3b3ac0d5e074a36dc5e407661ab59c2e0f255650ccd08ad1010fa0ea058` |
| results.json | 24042 | `76b21fae69616587fef2f45e387756734d22c101cd0baa7b399ff849f19dfcac` |

| 片段 | ASCII bytes，无末尾换行 | Git blob |
|---|---:|---|
| part-1.b64 | 4800 | `38c8296b2df02e0da8e18c82baa07bd732efae01` |
| part-2.b64 | 4800 | `5fc0909aa8a1ff27a7530b1a121c7bb172bffd93` |
| part-3.b64 | 4800 | `15938a998994c9166e7bcf4e7e284ad417a875c1` |
| part-4.b64 | 4228 | `15533a3fd6e55734796d4760d5c4db3a255572d5` |

只解码和验证，不执行任何payload：

```python
import base64, gzip, hashlib, io, json
from pathlib import Path

root = Path('docs/kernel-2.0-evidence/p3-17')
text = ''.join((root / f'part-{i}.b64').read_text(encoding='ascii') for i in range(1, 5))
assert len(text) == 18628
compressed = base64.b64decode(text, validate=True)
assert len(compressed) == 13969
assert hashlib.sha256(compressed).hexdigest() == '6440a9d006b9fe224bb3aaff0c64fe08b19a5532d0a5b8a54ec988953691bffd'
with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
    raw = stream.read(65537)
assert len(raw) == 56372
assert hashlib.sha256(raw).hexdigest() == '9ee80a25433135053ffee2ba4bf9281cf93670cc260da19145f150f29d647bf4'
value = json.loads(raw)
assert value['format'] == 'k2-p3-17-audit-text-bundle-v1'
assert set(value['files']) == {'README.md', 'check-wiring.py', 'results.json'}
expected = {
    'check-wiring.py': (27627, '57aac3b3ac0d5e074a36dc5e407661ab59c2e0f255650ccd08ad1010fa0ea058'),
    'results.json': (24042, '76b21fae69616587fef2f45e387756734d22c101cd0baa7b399ff849f19dfcac'),
}
for name, (size, digest) in expected.items():
    data = value['files'][name].encode('utf-8')
    assert len(data) == size and hashlib.sha256(data).hexdigest() == digest
result = json.loads(value['files']['results.json'])
assert len(result['checks']) == 27 and result['forbidden_effect_attempts'] == 0
print(result['totals'])
```

## 独立复现

先审阅完整脚本；从上述固定受信任M获取PINS中的21份原文件。`primitives.py/identity.py/market.py`在包根，`hithink.py`在adapters，其他在runtime；放入一个basename目录，脚本会先逐一核对原Git blob。不要从来源/生产ZIP取代码执行，不安装候选依赖来伪装原环境相符。

使用已有合格环境执行 `python check-wiring.py --sources ORIGINAL_SOURCE_DIRECTORY --out NEW_OUTPUT_PATH`；输出目录必须不存在。缺依赖或代码不符应报告真实边界，不放宽测试或hash。该命令是经审阅后显式调用的取证方式，不是日常工作流或自动重试权限。

较早的26项本地稿随后加强为本附件的27项：新增不同前驱run和非空无关lane，没有把一次合成run同时当作前驱与当前。Issue中的简短v1复现摘录不是此完整脚本，不能套用本附件hash；以本附件精确bytes为正式保管原件。P3继续，具体runtime修复、P4和生产效果均未获本附件授权。
