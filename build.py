"""slang.json + template.html → index.html

사용법: python3 build.py   (검증 실패 시 종료 코드 1, index.html은 건드리지 않음)
slang.json 한 줄 = ["단어", "카테고리", "뜻", "영어 예문", "한국어 번역"]
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
ASK = ["뭔 뜻이야 ㅋㅋ", "그게 뭔데", "?? 해석 좀"]  # index.html의 '내 질문' 말풍선 3종 순환


def slug(w):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", w.lower()))


def esc(t):
    # 원본 마크업 규칙: 따옴표만 &quot;, 아포스트로피는 그대로
    return html.escape(t, quote=False).replace('"', "&quot;")


def ex_html(ex, word):
    j = ex.lower().find(word.lower())
    return esc(ex[:j]) + "<b>" + esc(ex[j:j + len(word)]) + "</b>" + esc(ex[j + len(word):])


def check(rows):
    errors = []
    cats = list(dict.fromkeys(r[1] for r in rows))
    seen = {}
    for n, r in enumerate(rows, 1):
        if not (isinstance(r, list) and len(r) == 5 and all(isinstance(x, str) and x.strip() for x in r)):
            errors.append(f"{n}번: 문자열 5개가 아님 → {r!r}"); continue
        word, cat, mean, ex, ko = r
        key = slug(word)
        if key in seen:
            errors.append(f"{n}번 '{word}': {seen[key]}번과 중복(슬러그 '{key}')")
        seen[key] = n
        if word.lower() not in ex.lower():
            errors.append(f"{n}번 '{word}': 영어 예문에 단어가 그대로 들어 있어야 함 → {ex!r}")
        if len(cats) > 10 and cat == cats[-1]:
            errors.append(f"{n}번 '{word}': 새 카테고리 '{cat}' 금지(기존 10개 중 선택)")
    return errors


def build(rows):
    cats = list(dict.fromkeys(r[1] for r in rows))
    rooms = ['<button class="room" id="room-0" type="button" data-cat="전체" aria-pressed="true" style="--h:-1">'
             '<span class="rav all" aria-hidden="true">ALL</span><span class="rtext"><span class="rname">전체</span>'
             f'<span class="rprev" lang="en">{esc(rows[0][3])}</span></span><span class="badge">{len(rows)}</span></button>']
    sections, g = [], 0
    for i, cat in enumerate(cats):
        items = [r for r in rows if r[1] == cat]
        rooms.append(f'<button class="room" id="room-{i + 1}" type="button" data-cat="{esc(cat)}" aria-pressed="false" style="--h:{i}">'
                     f'<span class="rav" aria-hidden="true">{esc(cat[0])}</span><span class="rtext"><span class="rname">{esc(cat)}</span>'
                     f'<span class="rprev" lang="en">{esc(items[0][3])}</span></span><span class="badge">{len(items)}</span></button>')
        arts = []
        for word, _, mean, ex, ko in items:
            s = slug(word)
            arts.append(
                f'      <article class="thread reveal" id="{s}" aria-labelledby="n-{s}">\n'
                f'        <span class="av" aria-hidden="true">{esc(cat[0])}</span>\n'
                f'        <div class="who"><button class="name" id="n-{s}" type="button" title="뜻 복사">{esc(word)}</button><span class="cat">{esc(cat)}</span></div>\n'
                f'        <p class="bubble rcv ex" lang="en">{ex_html(ex, word)}</p>\n'
                f'        <p class="bubble snt"><span class="one" aria-hidden="true">1</span>{ASK[g % 3]}</p>\n'
                f'        <p class="bubble rcv re"><span class="txt"><span class="m">{esc(mean)}</span><br><span class="t">{esc(ko)}</span></span></p>\n'
                f'      </article>')
            g += 1
        sections.append(f'    <section class="sec" style="--h:{i}">\n      <div class="sentinel"></div>\n'
                        f'      <p class="pill spill">{esc(cat)} 방 · {len(items)}개</p>\n' + "\n".join(arts) + "\n    </section>")
    slang_js = "const SLANG = [\n" + ",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows) + \
               "\n].map(([word, cat, mean, ex, ko]) => ({ word, cat, mean, ex, ko }));"
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    out = tpl.replace("{{ROOMS}}", "\n    ".join(rooms)).replace("{{SECTIONS}}", "\n".join(sections)).replace("{{SLANG}}", slang_js)
    assert "{{" not in out, "템플릿 자리표시자가 남음"
    return out


if __name__ == "__main__":
    rows = json.loads((ROOT / "slang.json").read_text(encoding="utf-8"))
    errors = check(rows)
    if errors:
        print("slang.json 검증 실패:\n- " + "\n- ".join(errors)); sys.exit(1)
    (ROOT / "index.html").write_text(build(rows), encoding="utf-8")
    print(f"index.html 생성: 슬랭 {len(rows)}개, 카테고리 {len(set(r[1] for r in rows))}개")
