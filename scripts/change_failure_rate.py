"""
DORA Métrica #3 — Change Failure Rate (CFR)
────────────────────────────────────────────
Mide el porcentaje de despliegues a producción que causan fallos
y requieren un hotfix, rollback o revert.

Definición operativa:
  CFR = (PRs a main que son hotfix o revert) / (Total PRs mergeados a main) × 100

  Un PR se considera "fallo" si:
    - Su rama origen contiene: hotfix/, bugfix/, fix/, revert
    - O el título del PR contiene: hotfix, revert, rollback

Fuente de datos GitHub:
  - GET /repos/{owner}/{repo}/pulls?base=main&state=closed
  - Filtrar merged_at != null
  - Clasificar por nombre de rama y título

Salida (CSV por shard):
  repo_name, pr_number, title, source_branch, merged_to_main_at,
  is_failure, failure_reason, year_month
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from gh_helpers import get_repos_by_topic, get_prs, shard_slice

ORG = os.environ.get("GH_ORG", "CCAPITAL-APPS")
TOPIC = os.environ.get("GH_TOPIC", "tribu-canal-digital")
SHARDS = int(os.environ.get("SHARDS", "1"))
SHARD_ID = int(os.environ.get("SHARD_ID", "1"))
OUT_FILE = os.environ.get("OUT_FILE", f"cfr_shard_{SHARD_ID}_of_{SHARDS}.csv")

FROM_DATE = os.environ.get("FROM_DATE")
TO_DATE = os.environ.get("TO_DATE")
FROM_TS = pd.Timestamp(FROM_DATE) if FROM_DATE else None
TO_TS = pd.Timestamp(TO_DATE) if TO_DATE else None

# Patrones para detectar PRs de fallo/hotfix
FAILURE_BRANCH_PATTERNS = re.compile(
    r"^(hotfix|bugfix|fix|revert)[/\-]", re.IGNORECASE
)
FAILURE_TITLE_PATTERNS = re.compile(
    r"\b(hotfix|revert|rollback)\b", re.IGNORECASE
)


def classify_pr(pr):
    """Retorna (is_failure: bool, reason: str|None)."""
    branch = pr["head"]["ref"]
    title = pr.get("title", "")

    if FAILURE_BRANCH_PATTERNS.search(branch):
        return True, f"branch: {branch}"
    if FAILURE_TITLE_PATTERNS.search(title):
        return True, f"title: {title}"
    return False, None


def main():
    print(f"=== Change Failure Rate — Shard {SHARD_ID}/{SHARDS} — {ORG}/{TOPIC} ===")

    repos = get_repos_by_topic(ORG, TOPIC)
    repos.sort(key=lambda r: r["name"])
    shard_repos = shard_slice(repos, SHARDS, SHARD_ID)
    print(f"Repos a procesar: {[r['name'] for r in shard_repos]}")

    rows = []

    for repo in shard_repos:
        repo_name = repo["name"]
        print(f"\n── Repo: {repo_name} ──")

        main_prs = [p for p in get_prs(ORG, repo_name, "main") if p.get("merged_at")]
        print(f"  PRs merged → main: {len(main_prs)}")

        failures = 0
        counted = 0
        for pr in main_prs:
            merged_at = pd.Timestamp(pr["merged_at"])

            # Filtro opcional por rango de fechas (merge a main)
            if FROM_TS is not None and merged_at < FROM_TS:
                continue
            if TO_TS is not None and merged_at > TO_TS:
                continue

            counted += 1
            is_fail, reason = classify_pr(pr)
            if is_fail:
                failures += 1

            rows.append({
                "repo_name": repo_name,
                "pr_number": pr["number"],
                "title": pr.get("title", ""),
                "source_branch": pr["head"]["ref"],
                "merged_to_main_at": pr["merged_at"],
                "is_failure": is_fail,
                "failure_reason": reason,
                "year_month": merged_at.strftime("%Y-%m"),
            })

        cfr = (failures / counted * 100) if counted > 0 else 0
        print(f"  Failures: {failures}/{counted} = {cfr:.1f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False)
    print(f"\nExportados {len(df)} registros → {OUT_FILE}")


if __name__ == "__main__":
    main()
