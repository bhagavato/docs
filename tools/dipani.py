"""从 PDF 重建《三十七道品导引手册》的章节文件。

用法：
    python3 tools/dipani.py /path/to/Ledi_Sayadaw_Bodhipakkhiya_Dipani.pdf

幂等：重跑会覆盖 content/nirodha/dipani/ 下的 NN-*.md，输出应逐字节相同。
_index.md 是手写的，不由本脚本生成。
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pdftext as pt  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
DEST = REPO / "content" / "nirodha" / "dipani"
MARK = "\x01"

# 原书中以大字号单独成行的标题。逐行扫描全书短行后人工筛出，
# 已剔除折行产生的引文碎片（如「品·根相应第四·应观第八经）」）。
HEADINGS = [
    "中译音序言", "引言", "四种类别的人", "人的三种类型",
    "未了的行者与文句的行者的修行必备资粮", "关於这两种修行人",
    "未了的行者", "残存的文句行者", "圣人的时代",
    "戒律", "禅定", "智慧", "明与行",
    "只拥有“行”的结果", "只拥有“明”的结果", "根本的要点",
    "修行的次第与等待未来佛的人", "不需要固守既定的修行次第",
    "增上修行", "法障", "三十七道品",
    "四念住", "四正勤",
    "已生恶业与未生恶业", "已生善业与未生善业",
    "已生戒律与未生戒律", "已生禅定与未生禅定", "已生智慧与未生智慧",
    "四神足", "五  根", "五  力（balani）",
    "七觉支（Sambo jjhanga）", "八正道（Magganga）",
    "如何修持三十七道品", "佛法的遗产", "雷迪大师简介",
]

H2 = {
    "四种类别的人": "four-kinds", "人的三种类型": "three-types",
    "未了的行者与文句的行者的修行必备资粮": "requisites",
    "关於这两种修行人": "two-practitioners", "圣人的时代": "age-of-the-noble",
    "明与行": "vijja-carana", "根本的要点": "essentials",
    "修行的次第与等待未来佛的人": "order-of-practice",
    "增上修行": "higher-practice", "法障": "obstruction",
    "已生恶业与未生恶业": "arisen-unarisen-evil",
    "已生善业与未生善业": "arisen-unarisen-good",
    "已生戒律与未生戒律": "arisen-unarisen-sila",
    "已生禅定与未生禅定": "arisen-unarisen-samadhi",
    "已生智慧与未生智慧": "arisen-unarisen-panna",
}

H3 = {
    "未了的行者": "neyya", "残存的文句行者": "padaparama",
    "戒律": "sila", "禅定": "samadhi", "智慧": "panna",
    "只拥有“行”的结果": "carana-only", "只拥有“明”的结果": "vijja-only",
    "不需要固守既定的修行次第": "no-fixed-order",
}

# 条目缩进在全书不一致（p3 顶格、p10 缩进四格），因此不依赖缩进。
ITEM = re.compile(r"^\s*([一二三四五六七八九十]+)、\s*(.+)$")
# 限制为 1-2 位，否则「（1965）」这类年份会被误判为编号条目。
NUMBERED = re.compile(r"^\s*[（(](?:[一二三四五六七八九十]{1,3}|\d{1,2})[）)]")
SECTION_RULE = re.compile(r"^-{5,}\s*(.*)$", re.S)

# (起块, 止块, 文件名, 标题, book_number, 描述, linkTitle)。封面占 0-4 块，不入章节。
# linkTitle 只在需要与别处区分时给出，否则 Hugo 会回退到 title。
CHAPTERS = [
    (5, 13, "00-preface.md", "中译者序言", "序",
     "译者蔡文熙记述本书的翻译缘起、雷迪大师的地位，以及书名的几种译法。"),
    (13, 116, "01-introduction.md", "引言", 1,
     "四种类别的人与三种类型，修行必备的资粮，明与行，以及构成法障的十种事。"),
    (116, 127, "02-overview.md", "三十七道品", 2,
     "七组道品的总说：它们何以称为道品，以及彼此的关系。",
     # 书根的 linkTitle 也是「三十七道品」，侧栏与面包屑需要区分这一层
     "总说"),
    (127, 181, "03-satipatthana.md", "四念住", 3,
     "身、受、心、法四种念住，以及念住之於散乱心的对治。"),
    (181, 284, "04-sammappadhana.md", "四正勤", 4,
     "已生与未生的恶业、善业、戒律、禅定与智慧，各自对应的精进。"),
    (284, 330, "05-iddhipada.md", "四神足", 5,
     "欲、精进、心、观四种神足，成就世间与出世间事业的根本。"),
    (330, 397, "06-indriya.md", "五根", 6,
     "信、精进、念、定、慧五根，以及它们对治的五种烦恼。"),
    (397, 457, "07-bala.md", "五力", 7,
     "五根成熟为五力之後，不再为对立的烦恼所动摇。"),
    (457, 499, "08-bojjhanga.md", "七觉支", 8,
     "念、择法、精进、喜、轻安、定、舍七觉支的次第与作用。"),
    (499, 572, "09-magganga.md", "八正道", 9,
     "正见、正思惟乃至正定，以及八正道与戒定慧三学的对应。"),
    (572, 591, "10-practice.md", "如何修持三十七道品", 10,
     "从何处入手，以及在家修行人在今生可以着手的部分。"),
    (591, 728, "11-heritage.md", "佛法的遗产", 11,
     "佛陀留下的遗产、正法住世的条件，以及此时此地应当把握的事。"),
    (728, 755, "12-ledi-sayadaw.md", "雷迪大师简介", "附",
     "雷迪尊者（1846-1923）的生平、著作与影响。"),
]


def render(blocks, title):
    out, i = [], 0
    norm = lambda s: re.sub(r"\s+", "", s)                       # noqa: E731
    h2 = {norm(k): v for k, v in H2.items()}
    h3 = {norm(k): v for k, v in H3.items()}

    while i < len(blocks):
        b = blocks[i]
        if b.startswith(MARK):
            text = b[1:].strip()
            key = norm(text)
            if key in h2:
                out.append(f"## {text} {{#{h2[key]}}}")
            elif key in h3:
                out.append(f"### {text} {{#{h3[key]}}}")
            # 章一级的标题就是页面 title，正文里不再重复一次
            i += 1
            continue

        # 收集连续条目。序号回到「一」表示原书另起一组，不能并成同一个列表。
        run, expect = [], 1
        while i < len(blocks) and not blocks[i].startswith(MARK):
            m = ITEM.match(blocks[i])
            if not m or pt.cn_number(m.group(1)) != expect:
                break
            run.append(m.group(2).strip())
            expect += 1
            i += 1
        if len(run) >= 2:
            # 空行分隔的两个有序列表在 CommonMark 里会并成一个并续编号，
            # 原书另起的一组会被渲染成 5. 6. 7. 8.。注释节点强制断开列表。
            if out and out[-1].startswith("1. "):
                out.append("<!-- -->")
            out.append("\n".join(f"{n}. {t}" for n, t in enumerate(run, 1)))
            continue
        if run:
            out.append(blocks[i - 1])
            continue

        # 附录的脚注分隔线在原书里独占一行，重排时和第一条脚注粘在了一起。
        m = SECTION_RULE.match(b)
        if m:
            out.append("---")
            if m.group(1).strip():
                out.append(m.group(1).strip())
            i += 1
            continue

        out.append(b)
        i += 1
    return "\n\n".join(out)


def main(pdf):
    pages = pt.extract(pdf)
    lines = []
    for pg in sorted(pages):
        lines += pt.clean_page(pages[pg], drop_bare_numbers=True)
    blocks = pt.reflow(lines, full=76, headings=HEADINGS,
                       item=ITEM, numbered=NUMBERED, mark=MARK)

    ok, a, b = pt.lossless([pages[p] for p in sorted(pages)], blocks, MARK,
                           drop_bare_numbers=True)
    print(f"重排无损: {ok}  ({a} -> {b} 个非空白字符)")
    if not ok:
        raise SystemExit("重排丢字，已中止")

    for n, chapter in enumerate(CHAPTERS, 1):
        a0, b0, name, title, num, desc = chapter[:6]
        link = chapter[6] if len(chapter) > 6 else None
        body = render(blocks[a0:b0], title)
        head = ["---", f"title: {title}"]
        if link:
            head.append("# 书根的 linkTitle 也是「三十七道品」，侧栏与面包屑需要区分这一层。")
            head.append(f"linkTitle: {link}")
        head += [f"description: {desc}", "book_kind: chapter",
                 f"book_number: '{num}'", f"weight: {n * 10}", "---", ""]
        fm = "\n".join(head)
        (DEST / name).write_text(fm + body + "\n")
        print(f"  {name:<22} {b0 - a0:>3} 块 {len(body):>6} 字符")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
