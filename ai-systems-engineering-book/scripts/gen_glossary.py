"""Regenerate appendix-g-glossary.qmd from GLOSSARY.md."""
import re

GLOSSARY = "GLOSSARY.md"
OUT = "chapters/appendix/appendix-g-glossary.qmd"

g = open(GLOSSARY, encoding="utf-8").read()
out = ["---", 'title: "附录 G：术语表（Appendix G: Glossary）"', "---", "",
       "# 附录 G：术语表", "",
       "> 与 GLOSSARY.md 同步生成（scripts/gen_glossary.py）。定义以 GLOSSARY.md 为准。", ""]
m = re.search(r"```text\n(Prompt ≠ Context.*?)```", g, re.S)
out.append("## 概念边界\n\n```text\n" + (m.group(1) if m else "") + "```\n")
for cm in re.finditer(r"```yaml\nconcept:\n(.*?)```", g, re.S):
    body = cm.group(1)
    name = re.search(r"name: (\S+)", body)
    cn = re.search(r"chinese_name: (\S+)", body)
    deff = re.search(r"definition: (.*?)(?:\n  why_it_exists:|\n  prerequisites:)", body, re.S)
    if name and deff:
        d = deff.group(1).strip().replace("\n", " ").replace("  ", " ")
        out.append(f"**{name.group(1)}**（{cn.group(1) if cn else ''}）：{d}\n")
open(OUT, "w", encoding="utf-8").write("\n".join(out))
print("regenerated", OUT)
