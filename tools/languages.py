"""Recount the language bar and the repository count. Run on a signed-in Mac.

    python3 tools/languages.py && python3 tools/build_svg.py

Most of the code is in private repositories, which the scheduled workflow's
token cannot see, so this part of the card is refreshed by hand through the
`gh` CLI's own login. No token is read, stored or printed here.

Languages are GitHub-detected bytes across the repositories this account owns,
forks left out. Organisation repositories are not counted: their bytes are
mostly other people's code. `repositories` is every repository this account
has committed or opened a pull request in.
"""
import json
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERY = """
query($cursor: String) {
  viewer {
    repositoriesContributedTo(includeUserRepositories: true,
                              contributionTypes: [COMMIT, PULL_REQUEST]) { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: [OWNER], isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes { languages(first: 50) { edges { size node { name } } } }
    }
  }
}
"""


def gh_graphql(cursor):
    command = ["gh", "api", "graphql", "-f", f"query={QUERY}"]
    if cursor:
        command += ["-f", f"cursor={cursor}"]
    return json.loads(subprocess.run(command, check=True, capture_output=True,
                                     text=True).stdout)["data"]["viewer"]


def main():
    totals, cursor, contributed = {}, None, 0
    while True:
        viewer = gh_graphql(cursor)
        contributed = viewer["repositoriesContributedTo"]["totalCount"]
        page = viewer["repositories"]
        for repository in page["nodes"]:
            for edge in repository["languages"]["edges"]:
                name = edge["node"]["name"]
                totals[name] = totals.get(name, 0) + edge["size"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    payload = {
        "asOf": date.today().isoformat(),
        "repositories": contributed,
        "languages": [{"name": name, "bytes": size}
                      for name, size in sorted(totals.items(), key=lambda kv: -kv[1])],
    }
    (ROOT / "language_stats.json").write_text(json.dumps(payload, indent=2) + "\n",
                                              encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
