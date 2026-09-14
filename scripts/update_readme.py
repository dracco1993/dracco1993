"""Refresh README.md: latest merged PR per org repo, per-org merged PR and commit counts."""
import json, os, re, urllib.request

USER = "dracco1993"
LIMIT = 8
START, END = "<!-- recent_prs start -->", "<!-- recent_prs end -->"
PRS = re.compile(r"<!--prs:([^>]+)-->([^<]+)<!--/prs-->")
COMMITS = re.compile(r"<!--commits:([^>]+)-->([^<]+)<!--/commits-->")

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

def scope(name, exclude):
    """Org qualifier for a real org, or exclusion of every real org for the '__other' bucket."""
    return "".join(f"+-org:{o}" for o in exclude) if name.startswith("__") else f"+org:{name}"

def pr_count(name, exclude):
    q = f"author:{USER}+type:pr+is:merged{scope(name, exclude)}"
    return str(fetch(f"https://api.github.com/search/issues?q={q}&per_page=1")["total_count"])

def sig2(n):
    """Floor to two significant figures, so a '+' claim is always true."""
    d = len(str(n))
    if d <= 2:
        return n
    f = 10 ** (d - 2)
    return (n // f) * f

def commit_count(name, exclude):
    n = fetch(f"https://api.github.com/search/commits?q=author:{USER}{scope(name, exclude)}&per_page=1")["total_count"]
    return f"{sig2(n)}+"

def render(readme, rows, prs, commits):
    block = f"{START}\n" + "\n".join(rows) + f"\n{END}"
    readme = re.sub(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, readme, flags=re.S)
    readme = PRS.sub(lambda m: f"<!--prs:{m[1]}-->{prs.get(m[1], m[2])}<!--/prs-->", readme)
    readme = COMMITS.sub(lambda m: f"<!--commits:{m[1]}-->{commits.get(m[1], m[2])}<!--/commits-->", readme)
    return readme

def test():
    src = f"a\n{START}\nold\n{END}\nb"
    assert render(src, ["- x"], {}, {}) == f"a\n{START}\n- x\n{END}\nb"
    out = render(render(src, ["- x"], {}, {}), ["- y"], {}, {}); assert "- y" in out and "- x" not in out
    assert render("<!--prs:o-->1<!--/prs-->", [], {"o": "42"}, {}) == "<!--prs:o-->42<!--/prs-->"
    assert render("<!--commits:o-->9+<!--/commits-->", [], {}, {"o": "2000+"}) == "<!--commits:o-->2000+<!--/commits-->"
    assert [sig2(n) for n in (2033, 402, 152, 91, 7)] == [2000, 400, 150, 91, 7]
    assert scope("RAR1741", ["RAR1741", "TBA"]) == "+org:RAR1741"
    assert scope("__other", ["RAR1741", "TBA"]) == "+-org:RAR1741+-org:TBA"

if __name__ == "__main__":
    test()
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    orgs = {m[1] for m in PRS.finditer(readme)}
    corgs = {m[1] for m in COMMITS.finditer(readme)}
    real = sorted(o for o in orgs | corgs if not o.startswith("__"))
    out = render(readme, recent_prs(),
                 {o: pr_count(o, real) for o in orgs},
                 {o: commit_count(o, real) for o in corgs})
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
