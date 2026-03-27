"""
DORA Métrica #2 — Lead Time for Changes
────────────────────────────────────────
Mide el tiempo desde el PRIMER COMMIT en una feature branch hasta que llega
a producción (merge a main).

Flujo: feature → develop → qa → main.

Fuente de datos GitHub:
  - PRs mergeados a develop  → fecha merge = "llegó a develop"
  - PRs mergeados a qa       → fecha merge = "llegó a QA"
  - PRs mergeados a main     → fecha merge = "llegó a producción"
  - Compare API              → primer commit exclusivo de la feature branch
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from gh_helpers import (
    get_repos_by_topic, get_prs, get_pr_commits,
    api_get, shard_slice,
)

ORG = os.environ.get("GH_ORG", "CCAPITAL-APPS")
TOPIC = os.environ.get("GH_TOPIC", "tribu-canal-digital")
SHARDS = int(os.environ.get("SHARDS", "1"))
SHARD_ID = int(os.environ.get("SHARD_ID", "1"))
OUT_FILE = os.environ.get("OUT_FILE", f"lead_time_shard_{SHARD_ID}_of_{SHARDS}.csv")

FROM_DATE = os.environ.get("FROM_DATE")
TO_DATE = os.environ.get("TO_DATE")
FROM_TS = pd.Timestamp(FROM_DATE) if FROM_DATE else None
TO_TS = pd.Timestamp(TO_DATE) if TO_DATE else None


def get_branch_first_commit(org, repo_name, branch, base="develop"):
    """Primer commit exclusivo de `branch` vs `base` (fecha inicio del feature)."""
    url = f"https://api.github.com/repos/{org}/{repo_name}/compare/{base}...{branch}"
    resp = api_get(url)
    if resp is None:
        return None
    commits = resp.json().get("commits", [])
    if commits:
        return commits[0]["commit"]["author"]["date"]
    return None

def main():
    print(f"=== Lead Time — Shard {SHARD_ID}/{SHARDS} — {ORG}/{TOPIC} ===")

    repos = get_repos_by_topic(ORG, TOPIC)
    repos.sort(key=lambda r: r["name"])
    shard_repos = shard_slice(repos, SHARDS, SHARD_ID)
    print(f"Repos a procesar: {[r['name'] for r in shard_repos]}")

    rows = []

    for repo in shard_repos:
        repo_name = repo["name"]
        print(f"\n── Repo: {repo_name} ──")

        # 3. PRs mergeados → develop  (feature/fix/etc → develop)
        develop_prs = [p for p in get_prs(ORG, repo_name, "develop") if p.get("merged_at")]
        print(f"  PRs merged → develop: {len(develop_prs)}")

        # 4. PRs mergeados → qa  (develop → qa)
        qa_prs = [p for p in get_prs(ORG, repo_name, "qa") if p.get("merged_at")]
        print(f"  PRs merged → qa: {len(qa_prs)}")

        # 5. PRs mergeados → main  (qa → main)
        main_prs = [p for p in get_prs(ORG, repo_name, "main") if p.get("merged_at")]
        print(f"  PRs merged → main: {len(main_prs)}")

        # Indexar PRs qa/main por fecha para cruzarlos con develop
        # Estrategia: para cada PR a develop, buscamos el PR a qa cuyo merge_date
        # sea >= merge_date del PR a develop (el más cercano en tiempo).
        qa_prs_sorted = sorted(qa_prs, key=lambda p: p["merged_at"])
        main_prs_sorted = sorted(main_prs, key=lambda p: p["merged_at"])

        for pr in develop_prs:
            source_branch = pr["head"]["ref"]
            pr_number = pr["number"]
            merged_to_develop = pr["merged_at"]

            # Filtro opcional por rango de fechas usando el merge a develop
            merged_to_develop_ts = pd.Timestamp(merged_to_develop)
            if FROM_TS is not None and merged_to_develop_ts < FROM_TS:
                continue
            if TO_TS is not None and merged_to_develop_ts > TO_TS:
                continue

            # Primer commit del feature branch
            first_commit = get_branch_first_commit(ORG, repo_name, source_branch)

            # Fallback: primer commit del PR
            if not first_commit:
                commits = get_pr_commits(ORG, repo_name, pr_number)
                if commits:
                    first_commit = commits[0]["commit"]["author"]["date"]

            # Buscar PR a QA posterior al merge a develop (develop → qa)
            qa_match = None
            for qp in qa_prs_sorted:
                if qp["head"]["ref"] == "develop" and qp["merged_at"] >= merged_to_develop:
                    qa_match = qp
                    break

            # Buscar PR a main posterior al merge a qa (qa → main)
            main_match = None
            if qa_match:
                for mp in main_prs_sorted:
                    if mp["head"]["ref"] == "qa" and mp["merged_at"] >= qa_match["merged_at"]:
                        main_match = mp
                        break

            row = {
                "repo_name": repo_name,
                "source_branch": source_branch,
                "first_commit_date": first_commit,
                "pr_to_develop_id": pr_number,
                "merged_to_develop_at": merged_to_develop,
                "pr_to_qa_id": qa_match["number"] if qa_match else None,
                "merged_to_qa_at": qa_match["merged_at"] if qa_match else None,
                "pr_to_main_id": main_match["number"] if main_match else None,
                "merged_to_main_at": main_match["merged_at"] if main_match else None,
            }

            # Cycle time en días (primer commit → merge a main)
            if first_commit and row["merged_to_main_at"]:
                t0 = pd.Timestamp(first_commit)
                t1 = pd.Timestamp(row["merged_to_main_at"])
                row["cycle_time_days"] = round((t1 - t0).total_seconds() / 86400, 2)
            else:
                row["cycle_time_days"] = None

            rows.append(row)

    # 6. Exportar CSV
    columns = [
        "repo_name", "source_branch", "first_commit_date",
        "pr_to_develop_id", "merged_to_develop_at",
        "pr_to_qa_id", "merged_to_qa_at",
        "pr_to_main_id", "merged_to_main_at",
        "cycle_time_days",
    ]
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(OUT_FILE, index=False)
    print(f"\nExportados {len(df)} registros → {OUT_FILE}")


if __name__ == "__main__":
    main()