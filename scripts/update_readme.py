"""Rewrite the recent_prs block in README.md with the latest merged PR per repo."""
import json, os, re, urllib.request

USER = "dracco1993"
LIMIT = 8
START, END = "<!-- recent_prs start -->", "<!-- recent_prs end -->"

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if tok := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def recent_prs():
    q = f"author:{USER}+type:pr+is:merged+-repo:{USER}/{USER}"
    seen, rows = set(), []
    for page in range(1, 6):
        items = fetch(f"https://api.github.com/search/issues?q={q}&sort=updated&order=desc&per_page=100&page={page}")["items"]
        for it in items:
            repo = it["repository_url"].split("/repos/")[1]
            if repo in seen:
                continue
            seen.add(repo)
            rows.append(f"- [{repo}]({it['html_url']}) — {it['title']} ({it['closed_at'][:10]})")
            if len(rows) == LIMIT:
                return rows
        if len(items) < 100:
            break
    return rows

def render(readme, rows):
    block = f"{START}\n" + "\n".join(rows) + f"\n{END}"
    return re.sub(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, readme, flags=re.S)

def test():
    src = f"a\n{START}\nold\n{END}\nb"
    assert render(src, ["- x"]) == f"a\n{START}\n- x\n{END}\nb"
    out = render(render(src, ["- x"]), ["- y"]); assert "- y" in out and "- x" not in out

if __name__ == "__main__":
    test()
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(render(readme, recent_prs()))
