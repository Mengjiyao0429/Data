# -*- coding: utf-8 -*-
"""任务一（3）重复记录处理。

两级去重：
1. 精确去重：清洗后正文的 MD5 哈希；
2. 近似去重：字符级 shingle（默认 k=3）的 Jaccard 相似度，超过阈值视为重复。
长度差异过大的记录直接跳过比较，降低 O(n^2) 开销。
"""
import hashlib

from app import config


def _shingles(text, k=None):
    k = k or config.SHINGLE_K
    compact = "".join(text.split())
    if len(compact) < k:
        return {compact} if compact else set()
    return {compact[i:i + k] for i in range(len(compact) - k + 1)}


def _jaccard(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    if inter == 0:
        return 0.0
    return inter / len(set_a | set_b)


def dedup_records(records, threshold=None):
    """返回 (去重后保留记录, 移除数量)。"""
    threshold = threshold if threshold is not None else config.JACCARD_THRESHOLD
    kept = []
    kept_meta = []  # (length, shingles)
    seen_md5 = set()
    removed = 0

    for rec in records:
        content = rec.get("clean_content", "")
        digest = hashlib.md5(content.encode("utf-8")).hexdigest()
        if digest in seen_md5:
            removed += 1
            continue

        sh = _shingles(content)
        length = len("".join(content.split()))
        is_dup = False
        for kept_len, kept_sh in kept_meta:
            # 长度预筛：差异超过 30% 不可能达到高相似度
            if length and kept_len:
                if min(length, kept_len) / max(length, kept_len) < 0.7:
                    continue
            if _jaccard(sh, kept_sh) >= threshold:
                is_dup = True
                break

        if is_dup:
            removed += 1
            continue

        seen_md5.add(digest)
        kept_meta.append((length, sh))
        kept.append(rec)

    return kept, removed
