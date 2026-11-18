"""slang.json + template.html → index.html, page.html → w/<단어>.html·w/index.html, sitemap.xml

사용법: python3 build.py   (검증 실패 시 종료 코드 1, index.html은 건드리지 않음)
slang.json 한 줄 = ["단어", "카테고리", "뜻", "영어 예문", "한국어 번역"]
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "https://hyonnnnnn.github.io/no-cap/"
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
        if key in ('', 'index'):
            errors.append(f"{n}번 '{word}': 파일 이름으로 쓸 수 없는 단어")
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
    out = tpl.replace("{{ROOMS}}", "\n    ".join(rooms)).replace("{{SECTIONS}}", "\n".join(sections)).replace("{{SLANG}}", slang_js).replace("{{COUNT}}", str(len(rows)))
    assert "{{" not in out, "템플릿 자리표시자가 남음"
    return out


def pages(rows):
    """검색 유입용: 단어마다 한 장(w/<slug>.html) + 전체 목록(w/index.html). 반환값은 {파일명: html}"""
    shell = (ROOT / "page.html").read_text(encoding="utf-8")

    def page(title, desc, url, head, body):
        out = shell.replace("{{TITLE}}", esc(title)).replace("{{DESC}}", esc(desc)).replace("{{URL}}", url).replace("{{HEAD}}", head).replace("{{BODY}}", body)
        assert "{{" not in out, "page.html 자리표시자가 남음"
        return out

    def li(r):
        return f'<li><a href="{slug(r[0])}.html" lang="en">{esc(r[0])}</a> <span>{esc(r[2])}</span></li>'

    cats = list(dict.fromkeys(r[1] for r in rows))
    by_cat = {c: [r for r in rows if r[1] == c] for c in cats}
    out = {}
    for r in rows:
        word, cat, mean, ex, ko = r
        s, sib = slug(word), by_cat[cat]
        i = sib.index(r)
        near = sib[max(0, i - 4):i] + sib[i + 1:i + 5]  # 같은 카테고리의 앞뒤 4개씩만: 새 단어가 추가돼도 바뀌는 파일이 적음
        url = f"{BASE}w/{s}.html"
        ld = json.dumps({"@context": "https://schema.org", "@type": "DefinedTerm", "name": word, "description": mean, "url": url,
                         "inDefinedTermSet": {"@type": "DefinedTermSet", "name": "No Cap 영어 슬랭 사전", "url": BASE}}, ensure_ascii=False).replace("</", "<\\/")
        body = (f'<p class="cat">영어 슬랭 · {esc(cat)}</p>\n<h1><span lang="en">{esc(word)}</span> 뜻</h1>\n<p class="mean">{esc(mean)}</p>\n'
                f'<h2>예문</h2>\n<p class="bubble rcv" lang="en">{ex_html(ex, word)}</p>\n<p class="bubble snt">{esc(ko)}</p>\n'
                f'<a class="btn" href="../#{s}">단톡방에서 보기</a>\n<h2>{esc(cat)} 슬랭 더 보기</h2>\n<ul class="list">\n' + "\n".join(li(x) for x in near) + "\n</ul>")
        out[f"{s}.html"] = page(f"{word} 뜻 | 영어 슬랭 사전 No Cap", f"{word} 뜻: {mean}. 예문: {ex} ({ko})", url, f'<script type="application/ld+json">{ld}</script>', body)
    body = "<h1>영어 슬랭 전체 목록</h1>\n" + "\n".join(
        f'<h2>{esc(c)} · {len(by_cat[c])}개</h2>\n<ul class="list">\n' + "\n".join(li(x) for x in by_cat[c]) + "\n</ul>" for c in cats)
    out["index.html"] = page(f"영어 슬랭 전체 목록 {len(rows)}개 | No Cap", f"요즘 영어 슬랭 {len(rows)}개를 카테고리별로 모은 목록. 단어를 누르면 뜻과 예문을 볼 수 있어요.", f"{BASE}w/", "", body)
    return out


if __name__ == "__main__":
    rows = json.loads((ROOT / "slang.json").read_text(encoding="utf-8"))
    errors = check(rows)
    if errors:
        print("slang.json 검증 실패:\n- " + "\n- ".join(errors)); sys.exit(1)
    (ROOT / "index.html").write_text(build(rows), encoding="utf-8")
    made = pages(rows)
    assert len(made) == len(rows) + 1, "단어 페이지 수 불일치"
    wdir = ROOT / "w"
    wdir.mkdir(exist_ok=True)
    for old in wdir.glob("*.html"):
        if old.name not in made:
            old.unlink()  # slang.json에서 지운 단어의 페이지 정리
    for name, text in made.items():
        (wdir / name).write_text(text, encoding="utf-8")
    locs = [BASE, BASE + "w/"] + [BASE + "w/" + n for n in made if n != "index.html"]
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"  <url><loc>{u}</loc></url>\n" for u in locs) + "</urlset>\n", encoding="utf-8")
    print(f"index.html 생성: 슬랭 {len(rows)}개, 카테고리 {len(set(r[1] for r in rows))}개 / 단어 페이지 {len(made) - 1}장 + 목록 1장, sitemap {len(locs)}개 주소")
