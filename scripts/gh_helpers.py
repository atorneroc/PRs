"""Módulo compartido: helpers HTTP con paginación y rate-limit para GitHub API."""
import os
import sys
import time
import requests

TOKEN = os.environ.get("GH_TOKEN", "")
if not TOKEN:
    print("ERROR: La variable de entorno GH_TOKEN es requerida.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}


def api_get(url, params=None):
    """GET con manejo de rate-limit y reintentos."""
    while True:
        resp = requests.get(url, headers=HEADERS, params=params)

        if resp.status_code == 403:
            remaining = int(resp.headers.get("X-RateLimit-Remaining", 1))
            if remaining == 0:
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_ts - int(time.time()), 1) + 5
                print(f"  Rate-limit alcanzado. Esperando {wait}s …")
                time.sleep(wait)
                continue

        if resp.status_code == 200:
            return resp

        print(f"  Error {resp.status_code}: {url}")
        return None


def api_get_paginated(url, params=None):
    """Devuelve TODOS los items siguiendo el header Link: next."""
    items = []
    params = dict(params or {})
    params.setdefault("per_page", "100")

    while url:
        resp = api_get(url, params=params)
        if resp is None:
            break
        data = resp.json()
        if isinstance(data, list):
            items.extend(data)
        else:
            break

        url = None
        params = None
        link_header = resp.headers.get("Link", "")
        for part in link_header.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                break
    return items


def get_repos_by_topic(org, topic):
    """Repos de la org filtrados por topic."""
    url = f"https://api.github.com/orgs/{org}/repos"
    all_repos = api_get_paginated(url, {"type": "all", "per_page": "100"})
    filtered = [r for r in all_repos if topic in r.get("topics", [])]
    print(f"Total repos con topic '{topic}': {len(filtered)}")
    return filtered


def get_prs(org, repo_name, base, state="closed"):
    """PRs paginados hacia una rama base."""
    url = f"https://api.github.com/repos/{org}/{repo_name}/pulls"
    params = {"base": base, "state": state, "per_page": "100",
              "sort": "updated", "direction": "desc"}
    return api_get_paginated(url, params)


def get_pr_commits(org, repo_name, pr_number):
    """Commits de un PR (paginado)."""
    url = f"https://api.github.com/repos/{org}/{repo_name}/pulls/{pr_number}/commits"
    return api_get_paginated(url, {"per_page": "100"})


def shard_slice(items, shards, shard_id):
    """Retorna el subconjunto de items para el shard dado (1-based)."""
    total = len(items)
    chunk = total // shards
    remainder = total % shards
    start = (shard_id - 1) * chunk + min(shard_id - 1, remainder)
    end = start + chunk + (1 if shard_id <= remainder else 0)
    return items[start:end]
