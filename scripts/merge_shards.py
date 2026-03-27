"""
Consolida los CSVs de cada shard en reportes finales por métrica DORA
y genera un resumen ejecutivo.
"""
import glob
import os
import sys
import pandas as pd

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", ".")

METRIC_PATTERNS = {
    "deployment_frequency": "deploy_freq_shard_*.csv",
    "lead_time": "lead_time_shard_*.csv",
    "change_failure_rate": "cfr_shard_*.csv",
    "mttr": "mttr_shard_*.csv",
}


def merge_metric(name, pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  [{name}] Sin archivos.")
        return None
    print(f"  [{name}] Archivos: {files}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    out = os.path.join(OUTPUT_DIR, f"dora_{name}.csv")
    df.to_csv(out, index=False)
    print(f"  [{name}] {len(df)} filas → {out}")
    return df


def build_summary(dfs):
    """Genera un CSV resumen con las 4 métricas DORA agregadas por mes."""
    rows = []

    # Deployment Frequency: despliegues por mes
    df_df = dfs.get("deployment_frequency")
    if df_df is not None and not df_df.empty:
        grp = df_df.groupby("year_month").size().reset_index(name="deploys")
        for _, r in grp.iterrows():
            rows.append({
                "year_month": r["year_month"],
                "metric": "deployment_frequency",
                "value": r["deploys"],
                "unit": "deploys/month",
            })

    # Lead Time: mediana de cycle_time_days por mes
    df_lt = dfs.get("lead_time")
    if df_lt is not None and "cycle_time_days" in df_lt.columns:
        df_lt["year_month"] = pd.to_datetime(
            df_lt["merged_to_main_at"], errors="coerce"
        ).dt.strftime("%Y-%m")
        grp = df_lt.dropna(subset=["cycle_time_days"]).groupby("year_month")["cycle_time_days"]
        for month, vals in grp:
            rows.append({
                "year_month": month,
                "metric": "lead_time_median",
                "value": round(vals.median(), 2),
                "unit": "days",
            })

    # Change Failure Rate: % por mes
    df_cfr = dfs.get("change_failure_rate")
    if df_cfr is not None and not df_cfr.empty:
        grp = df_cfr.groupby("year_month")
        for month, g in grp:
            total = len(g)
            failures = g["is_failure"].sum()
            rows.append({
                "year_month": month,
                "metric": "change_failure_rate",
                "value": round(failures / total * 100, 1) if total > 0 else 0,
                "unit": "%",
            })

    # MTTR: promedio de recovery_hours por mes
    df_mttr = dfs.get("mttr")
    if df_mttr is not None and not df_mttr.empty:
        grp = df_mttr.groupby("year_month")["recovery_hours"]
        for month, vals in grp:
            rows.append({
                "year_month": month,
                "metric": "mttr",
                "value": round(vals.mean(), 2),
                "unit": "hours",
            })

    if rows:
        summary = pd.DataFrame(rows)
        summary.sort_values(["year_month", "metric"], inplace=True)
        out = os.path.join(OUTPUT_DIR, "dora_summary.csv")
        summary.to_csv(out, index=False)
        print(f"\n=== Resumen DORA → {out} ===")
        print(summary.to_string(index=False))
    else:
        print("\nNo hay datos suficientes para generar resumen.")


def main():
    print("=== Consolidando métricas DORA ===\n")
    dfs = {}
    for name, pattern in METRIC_PATTERNS.items():
        dfs[name] = merge_metric(name, pattern)

    build_summary(dfs)


if __name__ == "__main__":
    main()
