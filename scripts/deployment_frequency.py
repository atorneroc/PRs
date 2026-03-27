"""
DORA Métrica #1 — Deployment Frequency
───────────────────────────────────────
Mide con qué frecuencia se despliega a producción.

Definición operativa:
  Cada PR mergeado a `main` = 1 despliegue a producción.
  Se agrupa por semana y por mes para ver tendencias.

Fuente de datos GitHub:
  - GET /repos/{owner}/{repo}/pulls?base=main&state=closed
  - Filtrar solo los que tienen merged_at != null

Salida (CSV por shard):
  repo_name, pr_number, merged_to_main_at, source_branch, year_week, year_month
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from gh_helpers import get_repos_by_topic, get_prs, shard_slice

ORG = os.environ.get("GH_ORG", "CCAPITAL-APPS")
TOPIC = os.environ.get("GH_TOPIC", "tribu-canal-digital")
SHARDS = int(os.environ.get("SHARDS", "1"))
SHARD_ID = int(os.environ.get("SHARD_ID", "1"))
OUT_FILE = os.environ.get("OUT_FILE", f"deploy_freq_shard_{SHARD_ID}_of_{SHARDS}.csv")

FROM_DATE = os.environ.get("FROM_DATE")
TO_DATE = os.environ.get("TO_DATE")
FROM_TS = pd.Timestamp(FROM_DATE) if FROM_DATE else None
TO_TS = pd.Timestamp(TO_DATE) if TO_DATE else None


def main():
    print(f"=== Deployment Frequency — Shard {SHARD_ID}/{SHARDS} — {ORG}/{TOPIC} ===")

    repos = get_repos_by_topic(ORG, TOPIC)
    repos.sort(key=lambda r: r["name"])
    shard_repos = shard_slice(repos, SHARDS, SHARD_ID)
    print(f"Repos a procesar: {[r['name'] for r in shard_repos]}")

    rows = []

    for repo in shard_repos:
        repo_name = repo["name"]
        print(f"\n── Repo: {repo_name} ──")

        # PRs mergeados a main = despliegues a producción
        main_prs = [p for p in get_prs(ORG, repo_name, "main") if p.get("merged_at")]
        print(f"  Deploys (PRs merged → main): {len(main_prs)}")

        for pr in main_prs:
            merged_at = pd.Timestamp(pr["merged_at"])

            # Filtro opcional por rango de fechas (merge a main)
            if FROM_TS is not None and merged_at < FROM_TS:
                continue
            if TO_TS is not None and merged_at > TO_TS:
                continue

            rows.append({
                "repo_name": repo_name,
                "pr_number": pr["number"],
                "title": pr.get("title", ""),
                "source_branch": pr["head"]["ref"],
                "merged_to_main_at": pr["merged_at"],
                "year_week": merged_at.strftime("%Y-W%W"),
                "year_month": merged_at.strftime("%Y-%m"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False)
    print(f"\nExportados {len(df)} despliegues → {OUT_FILE}")


if __name__ == "__main__":
    main()
