# -*- coding: utf-8 -*-
"""公开探针集（内容公开）：站上“用我的 Key 测”功能在浏览器里发的就是这 8 条；我们的采集引擎每天在有 Key 的渠道上也发同样 8 条，
形成各模型的参考计数（tokref.json）。私有探针集另有一套，不在此文件。索引从 PUBLIC_BASE 起，与私有集分开存。"""
PUBLIC_PROBES = [
    "Sinan probe 01: The quick brown fox jumps over the lazy dog.",
    "司南探针 02：实付价放在同一把尺上，官方价永远在 100% 中线。",
    "Sinan probe 03: 👨‍👩‍👧‍👦 🧭 🚀 emoji + 中英混排 mixed script",
    "Sinan probe 04: def f(x):\n    return [i*i for i in range(x)]\n",
    "Sinan probe 05: 2.718281828459045235360287471352662497757",
    "Sinan probe 06: Ünïcödé façade naïve résumé Zürich Привет Γειά مرحبا",
    "Sinan probe 07: 龘齉爩鱻麤龗 生僻字 measurement not judgement",
    "Sinan probe 08: https://compute.sinanlab.com/rank?week=2026-w36#board",
]
PUBLIC_BASE = 100
