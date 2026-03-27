"""
DORA Métrica #4 — Mean Time to Recovery (MTTR)
───────────────────────────────────────────────
Mide el tiempo promedio para recuperarse de un fallo en producción.

Definición operativa:
  Para cada PR de tipo hotfix/revert mergeado a main:
    MTTR = merged_at  −  created_at  del PR

  Esto captura el tiempo desde que se detectó el problema (se creó el PR
  de corrección) hasta que se resolvió (se mergeó a producción).

  Alternativa más precisa (si disponible):
    Si el PR referencia un Issue, se usa la fecha de creación del Issue
    como inicio del incidente.

Fuente de datos GitHub:
  - PRs mergeados a main cuya rama o título indique hotfix/revert/rollback
  - Fecha created_at del PR (o del Issue referenciado)
  - Fecha merged_at del PR

Salida (CSV por shard):
  repo_name, pr_number, title, source_branch, created_at,
  merged_to_main_at, recovery_hours, year_month
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from gh_helpers import get_repos_by_topic, get_prs, api_get, shard_slice

ORG = os.environ.get("GH_ORG", "CCAPITAL-APPS")
TOPIC = os.environ.get("GH_TOPIC", "tribu-canal-digital")
SHARDS = int(os.environ.get("SHARDS", "1"))
SHARD_ID = int(os.environ.get("SHARD_ID", "1"))
OUT_FILE = os.environ.get("OUT_FILE", f"mttr_shard_{SHARD_ID}_of_{SHARDS}.csv")

FROM_DATE = os.environ.get("FROM_DATE")
TO_DATE = os.environ.get("TO_DATE")
FROM_TS = pd.Timestamp(FROM_DATE) if FROM_DATE else None
TO_TS = pd.Timestamp(TO_DATE) if TO_DATE else None

FAILURE_BRANCH_PATTERNS = re.compile(
    r"^(hotfix|bugfix|fix|revert)[/\-]", re.IGNORECASE
)
FAILURE_TITLE_PATTERNS = re.compile(
    r"\b(hotfix|revert|rollback)\b", re.IGNORECASE
)


def is_failure_pr(pr):
    branch = pr["head"]["ref"]
    title = pr.get("title", "")
    return bool(
        FAILURE_BRANCH_PATTERNS.search(branch)
        or FAILURE_TITLE_PATTERNS.search(title)
    )


def get_linked_issue_created_at(org, repo_name, pr_number):
    """Intenta obtener la fecha de creación del issue vinculado al PR via timeline."""
    url = f"https://api.github.com/repos/{org}/{repo_name}/issues/{pr_number}/timeline"
    resp = api_get(url, params={"per_page": "100"})
    if resp is None:
        return None
    events = resp.json()
    if not isinstance(events, list):
        return None
    for event in events:
        if event.get("event") == "cross-referenced":
            source = event.get("source", {}).get("issue", {})
            if source.get("created_at"):
                return source["created_at"]
    return None


def main():
    print(f"=== MTTR — Shard {SHARD_ID}/{SHARDS} — {ORG}/{TOPIC} ===")

    repos = get_repos_by_topic(ORG, TOPIC)
    repos.sort(key=lambda r: r["name"])
    shard_repos = shard_slice(repos, SHARDS, SHARD_ID)
    print(f"Repos a procesar: {[r['name'] for r in shard_repos]}")

    rows = []

    for repo in shard_repos:
        repo_name = repo["name"]
        print(f"\n── Repo: {repo_name} ──")

        main_prs = [p for p in get_prs(ORG, repo_name, "main") if p.get("merged_at")]
        failure_prs = [p for p in main_prs if is_failure_pr(p)]
        print(f"  Hotfix/Revert PRs: {len(failure_prs)} de {len(main_prs)} totales")

        for pr in failure_prs:
            pr_number = pr["number"]
            created_at = pr["created_at"]
            merged_at = pr["merged_at"]

            t1 = pd.Timestamp(merged_at)

            # Filtro opcional por rango de fechas (resolución del incidente)
            if FROM_TS is not None and t1 < FROM_TS:
                continue
            if TO_TS is not None and t1 > TO_TS:
                continue

            # Intentar obtener fecha más precisa desde un issue vinculado
            issue_created = get_linked_issue_created_at(ORG, repo_name, pr_number)
            incident_start = issue_created or created_at

            t0 = pd.Timestamp(incident_start)
            recovery_hours = round((t1 - t0).total_seconds() / 3600, 2)

            rows.append({
                "repo_name": repo_name,
                "pr_number": pr_number,
                "title": pr.get("title", ""),
                "source_branch": pr["head"]["ref"],
                "incident_start": incident_start,
                "incident_source": "issue" if issue_created else "pr_created",
                "merged_to_main_at": merged_at,
                "recovery_hours": recovery_hours,
                "year_month": t1.strftime("%Y-%m"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False)

    if not df.empty:
        avg_hours = df["recovery_hours"].mean()
        print(f"\nMTTR promedio: {avg_hours:.1f} horas")
    print(f"Exportados {len(df)} incidentes → {OUT_FILE}")


if __name__ == "__main__":
    main()
