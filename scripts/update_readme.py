"""Refresh README.md: latest merged PR per org repo, and per-org merged PR counts."""
import json, os, re, urllib.request

USER = "dracco1993"
LIMIT = 8
START, END = "<!-- recent_prs start -->", "<!-- recent_prs end -->"
COUNT = re.compile(r"<!--prs:([^>]+)-->(\d+)<!--/prs-->")

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if tok := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def recent_prs():
    q = f"author:{USER}+type:pr+is:merged+-user:{USER}"
    seen, rows = set(), []
    for page in range(1, 6):
        items = fetch(f"https://api.github.com/search/issues?q={q}&sort=updated&order=desc&per_page=100&page={page}")["items"]
        for it in items:
            repo = it["repository_url"].split("/repos/")[1]
            if repo in seen:
                continue
            seen.add(repo)
            rows.append((it["closed_at"][:10], f"- [{repo}]({it['html_url']}) — {it['title']}"))
            if len(rows) == LIMIT:
                break
        if len(rows) == LIMIT or len(items) < 100:
            break
    return [f"{line} ({date})" for date, line in sorted(rows, reverse=True)]

def org_count(org):
    return fetch(f"https://api.github.com/search/issues?q=author:{USER}+type:pr+is:merged+org:{org}&per_page=1")["total_count"]

def render(readme, rows, counts):
    block = f"{START}\n" + "\n".join(rows) + f"\n{END}"
    readme = re.sub(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, readme, flags=re.S)
    return COUNT.sub(lambda m: f"<!--prs:{m[1]}-->{counts.get(m[1], m[2])}<!--/prs-->", readme)

def test():
    src = f"a\n{START}\nold\n{END}\nb"
    assert render(src, ["- x"], {}) == f"a\n{START}\n- x\n{END}\nb"
    out = render(render(src, ["- x"], {}), ["- y"], {}); assert "- y" in out and "- x" not in out
    assert render("<!--prs:o-->1<!--/prs--> <!--prs:z-->7<!--/prs-->", [], {"o": 42}) == "<!--prs:o-->42<!--/prs--> <!--prs:z-->7<!--/prs-->"

if __name__ == "__main__":
    test()
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    orgs = {m[1] for m in COUNT.finditer(readme)}
    out = render(readme, recent_prs(), {o: org_count(o) for o in orgs})
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
