"""把有文本层的 PDF 还原成段落，供生成 Book 章节使用。

这里只放与具体书无关的部分。每本书的章节切分、标题层级、页眉形态各不相同，
写成独立的配置脚本，见 tools/README.md。

## 为什么重排需要两个信号

PDF 的文本层按版面行存放，行尾都是硬换行。只按标点判断段落结束会错：整行排满
但句子没结束的行会被断开。只按行宽判断也会错：最后一行恰好排满的段落会被连上
下一段。两者并联——出现终止标点，**或者**这一行没排到右边界——才能还原原文。

验收方式是去掉两边所有空白后逐字比对；《三十七道品导引手册》全书 60,464 个
非空白字符，重排前后完全一致。
"""
import pathlib
import re
import unicodedata

TERMINAL = "。！？…"
CLOSERS = "」』）】〕”’》"
BARE_NUM = re.compile(r"^\s*\d{1,3}\s*$")
FOOTNOTE = re.compile(r"^(\d{1,3})[\t ]\s*(.*)$")


def width(s):
    """显示宽度：CJK 与全角算两格，其余算一格。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s.rstrip())


def extract(pdf_path, cache=None):
    """抽出每页文本，返回 {页号: 文本}。页号从 1 起，与 PDF 阅读器一致。

    cache 指向一个 .txt 时，第一次抽取后写入，之后直接复用——抽取 400 页要几十秒。
    """
    if cache is not None:
        cache = pathlib.Path(cache)
        if cache.exists():
            return _parse_cache(cache.read_text())

    from pypdf import PdfReader                      # 仅在真正抽取时才需要

    reader = PdfReader(str(pdf_path))
    pages = {i: (p.extract_text() or "") for i, p in enumerate(reader.pages, 1)}
    if cache is not None:
        cache.write_text(
            "".join(f"\n\n===== PAGE {n} =====\n{t}" for n, t in sorted(pages.items()))
        )
    return pages


def _parse_cache(text):
    parts = re.split(r"\n\n===== PAGE (\d+) =====\n", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def clean_page(body, header=None, drop_bare_numbers=False):
    """去掉页眉与孤立数字行，返回正文行（保留行尾空格，重排时要用）。

    drop_bare_numbers 用于把边注形式的原著页码剔除；页码本身若印在页眉里，
    交给 header 正则处理。
    """
    out = []
    for line in body.split("\n"):
        if not line.strip():
            continue
        if header is not None and header.match(line):
            continue
        if drop_bare_numbers and BARE_NUM.match(line):
            continue
        out.append(line)
    return out


def ends_block(line, full):
    """这一行是不是段落结尾。见模块开头对两个信号的说明。"""
    s = line.rstrip()
    if not s:
        return True
    ch = s[-1]
    while ch in CLOSERS and len(s) > 1:              # 收尾引号/括号前再看一位
        s = s[:-1].rstrip()
        ch = s[-1] if s else ""
    if ch in TERMINAL or ch == "：":
        return True
    return width(line) < full


def reflow(lines, full, headings=(), item=None, numbered=None, mark=""):
    """把硬换行的行还原成块。

    full      正文满行的显示宽度下界；低于它视为作者主动断行。
    headings  这些行不参与拼接，各自独立成块并加上 mark 前缀。
    item      条目正则（如「一、」）；匹配的行强制另起一块。
    numbered  编号条目正则（如「（一）」）；同上。
    """
    heading_keys = {re.sub(r"\s+", "", h) for h in headings}
    blocks, buf = [], ""
    for line in lines:
        stripped = line.strip()
        if re.sub(r"\s+", "", stripped) in heading_keys:
            if buf:
                blocks.append(buf)
                buf = ""
            blocks.append(mark + stripped)
            continue
        starts_new = bool((item and item.match(line)) or (numbered and numbered.match(line)))
        if starts_new and buf:
            blocks.append(buf)
            buf = ""
        buf += line if not buf else line.lstrip()
        if ends_block(line, full):
            blocks.append(buf)
            buf = ""
    if buf:
        blocks.append(buf)
    return [re.sub(r"\s+", " ", b).strip() for b in blocks if b.strip()]


def split_footnotes(lines, expect):
    """按「期望编号」切开正文与页脚脚注，返回 (正文行, 脚注行, 新的期望号)。

    不能靠模式匹配：正文里以数字开头的行可能很多（一本学术专著里有七百多处）。只有恰好等于
    本章下一个脚注号的那一行才是分界。脚注标记后可能是「TAB + 空格」，所以分隔符
    之后允许再有空白——漏掉这点会让整章脚注混进正文。
    """
    for i, line in enumerate(lines):
        m = FOOTNOTE.match(line)
        if m and int(m.group(1)) == expect:
            notes = lines[i:]
            for l in notes:
                m2 = FOOTNOTE.match(l)
                if m2 and int(m2.group(1)) == expect:
                    expect += 1
            return lines[:i], notes, expect
    return lines, [], expect


def group_notes(lines):
    """把脚注行按编号聚合成 [(号, 文本)]，续行并入上一条。"""
    notes, cur, num = [], "", None
    for line in lines:
        m = FOOTNOTE.match(line)
        if m and (num is None or int(m.group(1)) == num + 1):
            if num is not None:
                notes.append((num, cur))
            num, cur = int(m.group(1)), m.group(2)
        else:
            cur += line.strip() if cur.endswith(" ") else line.strip()
    if num is not None:
        notes.append((num, cur))
    return [(n, re.sub(r"\s+", " ", t).strip()) for n, t in notes]


def lossless(raw_pages, blocks, mark="", drop_bare_numbers=False):
    """去掉全部空白后逐字比对，确认重排没有丢字。

    顺序要紧：孤立数字行必须在压掉空白之前剔除。先压空白就没有行边界了，
    多行模式再也匹配不到，校验会凭空多出全部页码的位数而误报丢字。
    """
    # 必须用换行拼接：页码印在页末，直接相接会和下一页首行粘成一行。
    src = "\n".join(raw_pages)
    if drop_bare_numbers:
        src = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", src)
    src = re.sub(r"\s", "", src)
    dst = re.sub(r"\s", "", "".join(b.lstrip(mark) for b in blocks))
    return src == dst, len(src), len(dst)


CN_DIGIT = {c: i for i, c in enumerate("一二三四五六七八九", 1)}


def cn_number(s):
    """把「一」「十」「十一」「二十」这类中文序数转成整数。"""
    if s == "十":
        return 10
    if "十" in s:
        head, _, tail = s.partition("十")
        return CN_DIGIT.get(head, 1) * 10 + CN_DIGIT.get(tail, 0)
    return CN_DIGIT.get(s, 0)
