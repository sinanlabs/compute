# sinan-probe

用你自己的 Key，在终端里测一个模型 API 中转站。单文件、只依赖 Python 3 标准库，Key 不离开你的电脑。

```bash
curl -O https://raw.githubusercontent.com/sinanlabs/compute/main/cli/sinan_probe.py
python3 sinan_probe.py toapis.cn sk-你的Key --models gpt-5.6-luna,claude-sonnet-5
python3 sinan_probe.py toapis.cn sk-你的Key --all
```

它做三件事：向每个模型发 8 条公开探针串（每条只要 4 个输出 token，一次几厘钱），比对返回的 token 计数与司南从多个渠道得到的参考计数；记首字节延迟 p50；看回显的模型名是否与请求一致。判定只有四种：**一致 / 含固定前缀 / 不一致 / 无参考**。

"不一致"只表示该渠道对同一输入返回的 token 计数与多渠道共识不同，成因很多（上游分流、系统提示注入、量化、缓存），工具不推测。这是一致性测量，不是真伪判定。

参考计数每日更新：https://compute.sinanlab.com/assets/tokref.json  ·  网页版：https://compute.sinanlab.com/check  ·  口径：https://compute.sinanlab.com/method
