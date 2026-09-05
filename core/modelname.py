# -*- coding: utf-8 -*-
"""模型名归一。中转站写 claude-opus-4-6，OpenRouter 写 anthropic/claude-opus-4.6，
DeepSeek 官方写 deepseek-v3.2 —— 不归一就对不上。

规则尽量少、可解释、可回溯。归一失败就不匹配，绝不猜。
"""
from __future__ import unicode_literals
import re

_PREFIX = re.compile(r"^[a-z0-9_-]+/")                     # anthropic/ openai/ x-ai/
_SUFFIX = re.compile(r":(batch|free|extended|thinking|online|nitro|floor)$")
_VERDASH = re.compile(r"(?<=\d)-(?=\d)")                   # 4-6 -> 4.6，只在数字之间
_DATE = re.compile(r"[-.](?:20\d{2}[.-]\d{2}[.-]\d{2}|20\d{6}|\d{6}|\d{4})$")   # -20250514 / .2025.08.07 / -250528 / -0905
_RELAYSFX = re.compile(r"-(official|preview|latest|stable|thinking|nothinking|non-thinking)$")   # 中转站自加/同价模式后缀
_SPACES = re.compile(r"\s+")


def canonical(name):
    if not name:
        return None
    n = name.strip().lower()
    n = _SPACES.sub("-", n)
    n = _PREFIX.sub("", n)
    n = _SUFFIX.sub("", n)
    n = _VERDASH.sub(".", n)          # 先把数字间 - 变 .，日期就统一成 .2025.08.07 形态
    n = _DATE.sub("", n)
    n = _RELAYSFX.sub("", n)
    n = _DATE.sub("", n)               # -thinking 去掉后可能又露出日期
    n = n.replace("_", "-")
    return n


def same_model(a, b):
    ca, cb = canonical(a), canonical(b)
    return bool(ca) and ca == cb


if __name__ == "__main__":
    pairs = [("claude-opus-4-6", "anthropic/claude-opus-4.6"),
             ("claude-sonnet-4-5", "anthropic/claude-sonnet-4.5:batch"),
             ("gpt-5.4", "openai/gpt-5.4"),
             ("deepseek-v3.2-exp", "deepseek/deepseek-v3.2-exp"),
             ("Gemini-2.5-Pro", "google/gemini-2.5-pro"),
             ("kimi-k2-0905", "moonshotai/kimi-k2-0905"),
             ("gpt-5.4-mini", "openai/gpt-5.4"),          # 应当不同
             ("claude-opus-4-6", "claude-opus-4-7")]      # 应当不同
    for a, b in pairs:
        print("%-5s %-24s ~ %-40s  -> %s" % (same_model(a, b), a, b, canonical(a)))
