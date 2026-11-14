import io
import requests
import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor, Ridge

# Batman ve Güneydoğu Anadolu Pilot Kutusu (Min Lat, Min Lon, Max Lat, Max Lon)
DEFAULT_BBOX = (36.80, 39.50, 38.80, 43.00)


def _haversine_matrix_km(lat1, lon1, lat2, lon2):
    """Vektörize Haversine mesafe matrisi (km) — döngüsüz, yüksek hızlı."""
    r = 6371.0088
    lat1_r = np.radians(lat1)[:, None]
    lon1_r = np.radians(lon1)[:, None]
    lat2_r = np.radians(lat2)[None, :]
    lon2_r = np.radians(lon2)[None, :]

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def parse_and_filter_aoi(df, source_tag="UNKNOWN", filter_bbox=True, bbox=DEFAULT_BBOX):
    """NASA FIRMS CSV/API verisini standartlaştırır, zaman damgalarını ve AOI filtresini uygular."""
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "latitude", "longitude", "acq_date", "acq_time", "satellite",
            "frp", "daynight", "type", "datetime", "date_str", "year", "month", "source"
        ])

    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]

    if "latitude" not in d.columns or "longitude" not in d.columns:
        return pd.DataFrame()

    d["latitude"] = pd.to_numeric(d["latitude"], errors="coerce")
    d["longitude"] = pd.to_numeric(d["longitude"], errors="coerce")
    d = d.dropna(subset=["latitude", "longitude"])

    if filter_bbox and bbox is not None:
        min_lat, min_lon, max_lat, max_lon = bbox
        d = d[
            (d["latitude"] >= min_lat) & (d["latitude"] <= max_lat) &
            (d["longitude"] >= min_lon) & (d["longitude"] <= max_lon)
        ].copy()

    if d.empty:
        return pd.DataFrame(columns=[
            "latitude", "longitude", "acq_date", "acq_time", "satellite",
            "frp", "daynight", "type", "datetime", "date_str", "year", "month", "source"
        ])

    d["frp"] = pd.to_numeric(d.get("frp", 0.0), errors="coerce").fillna(0.0).clip(lower=0.0)

    if "type" in d.columns:
        d["type"] = pd.to_numeric(d["type"], errors="coerce").fillna(0).astype(int)
    else:
        d["type"] = 0

    if "satellite" in d.columns:
        d["satellite"] = d["satellite"].astype(str).str.strip()
    else:
        d["satellite"] = "Aqua" if "MODIS" in source_tag.upper() else "N20"

    if "daynight" in d.columns:
        d["daynight"] = d["daynight"].astype(str).str.strip().str.upper()
    else:
        d["daynight"] = "D"

    acq_date_str = d["acq_date"].astype(str).str.strip() if "acq_date" in d.columns else "2025-07-01"
    if "acq_time" in d.columns:
        acq_time_str = (
            pd.to_numeric(d["acq_time"], errors="coerce")
            .fillna(1330)
            .astype(int)
            .astype(str)
            .str.zfill(4)
        )
    else:
        acq_time_str = "1330"

    d["datetime"] = pd.to_datetime(
        acq_date_str + " " + acq_time_str.str.slice(0, 2) + ":" + acq_time_str.str.slice(2, 4),
        errors="coerce"
    )
    d = d.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)

    d["date_str"] = d["datetime"].dt.strftime("%Y-%m-%d")
    d["year"] = d["datetime"].dt.year
    d["month"] = d["datetime"].dt.month
    d["source"] = source_tag
    return d


def fetch_firms_nrt(api_key, sensor="MODIS_NRT", days=5, bbox=DEFAULT_BBOX):
    """NASA FIRMS Canlı NRT API'sinden veri çeker."""
    if not api_key or len(str(api_key).strip()) < 5:
        return pd.DataFrame(), "EKSİK_API_KEY"

    min_lat, min_lon, max_lat, max_lon = bbox
    area_coords = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    days_clamped = int(np.clip(days, 1, 10))
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key.strip()}/{sensor}/{area_coords}/{days_clamped}"

    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200 or "Invalid" in resp.text or "exceeded" in resp.text.lower():
            return pd.DataFrame(), f"API_HATA_{resp.status_code}"
        raw_df = pd.read_csv(io.StringIO(resp.text))
        if raw_df.empty or "latitude" not in raw_df.columns:
            return pd.DataFrame(), "VERİ_YOK"
        parsed = parse_and_filter_aoi(raw_df, sensor, filter_bbox=True, bbox=bbox)
        return parsed, "OK"
    except Exception as exc:
        return pd.DataFrame(), f"BAĞLANTI_HATASI ({type(exc).__name__})"


def match_aqua_and_viirs(modis_df, viirs_df, max_dist_km=2.0, max_time_min=120, include_terra=False):
    """Gün bazlı bloklanmış vektörize uzay-zaman eşleştirmesi (Aqua MODIS & VIIRS)."""
    summary = {
        "aqua_records": 0,
        "terra_records": 0,
        "viirs_records": int(len(viirs_df)) if viirs_df is not None else 0,
        "matched_aqua_events": 0,
        "aqua_codetection_pct": 0.0,
        "independent_days": 0,
        "median_time_diff_min": 0.0
    }

    if modis_df is None or modis_df.empty or viirs_df is None or viirs_df.empty:
        return pd.DataFrame(), summary

    sat_upper = modis_df["satellite"].astype(str).str.upper()
    is_terra = sat_upper.str.contains("TERRA") | (sat_upper == "T")
    is_aqua = sat_upper.str.contains("AQUA") | (sat_upper == "A") | (~is_terra)

    summary["aqua_records"] = int(is_aqua.sum())
    summary["terra_records"] = int(is_terra.sum())

    m_work = modis_df if include_terra else modis_df[is_aqua].copy()
    if m_work.empty:
        return pd.DataFrame(), summary

    m_years = set(m_work["year"].dropna().unique())
    v_years = set(viirs_df["year"].dropna().unique())
    if m_years and v_years and m_years.isdisjoint(v_years):
        summary["warning"] = f"⚠️ Yüklenen MODIS ({sorted(m_years)}) ve VIIRS ({sorted(v_years)}) dosyalarının yılları birbiriyle örtüşmüyor!"
        return pd.DataFrame(), summary

    v_groups = {dt: grp for dt, grp in viirs_df.groupby("date_str")}
    matched_rows = []

    for dt_str, m_grp in m_work.groupby("date_str"):
        v_grp = v_groups.get(dt_str)
        if v_grp is None or v_grp.empty:
            continue

        m_lats = m_grp["latitude"].to_numpy()
        m_lons = m_grp["longitude"].to_numpy()
        m_times = (m_grp["datetime"].astype("int64") // 10**9).to_numpy() / 60.0
        m_frps = m_grp["frp"].to_numpy()
        m_years_arr = m_grp["year"].to_numpy()
        m_months_arr = m_grp["month"].to_numpy()

        v_lats = v_grp["latitude"].to_numpy()
        v_lons = v_grp["longitude"].to_numpy()
        v_times = (v_grp["datetime"].astype("int64") // 10**9).to_numpy() / 60.0
        v_frps = v_grp["frp"].to_numpy()

        dist_mat = _haversine_matrix_km(m_lats, m_lons, v_lats, v_lons)
        time_mat = np.abs(v_times[None, :] - m_times[:, None])
        valid_mask = (dist_mat <= max_dist_km) & (time_mat <= max_time_min)

        for i in range(len(m_grp)):
            idx = np.where(valid_mask[i])[0]
            if idx.size > 0:
                matched_rows.append({
                    "date_str": dt_str,
                    "year": int(m_years_arr[i]),
                    "month": int(m_months_arr[i]),
                    "latitude": float(m_lats[i]),
                    "longitude": float(m_lons[i]),
                    "aqua_frp": float(m_frps[i]),
                    "viirs_frp_sum": float(v_frps[idx].sum()),
                    "viirs_frp_mean": float(v_frps[idx].mean()),
                    "viirs_pixel_count": int(idx.size),
                    "min_dist_km": float(dist_mat[i, idx].min()),
                    "median_time_diff_min": float(np.median(time_mat[i, idx]))
                })

    pairs_df = pd.DataFrame(matched_rows)
    if not pairs_df.empty:
        summary["matched_aqua_events"] = int(len(pairs_df))
        denom = max(len(m_work), 1)
        summary["aqua_codetection_pct"] = round(100.0 * len(pairs_df) / denom, 1)
        summary["independent_days"] = int(pairs_df["date_str"].nunique())
        summary["median_time_diff_min"] = round(float(pairs_df["median_time_diff_min"].median()), 1)

    return pairs_df, summary


def compute_detectability_curve(modis_df, viirs_df, max_dist_km=2.0, max_time_min=120, include_terra=False):
    """VIIRS FRP dilimlerine göre MODIS yakalama oranını (gözlenen alt sınır) hesaplar."""
    bins = [0, 5, 10, 20, 40, 80, 10000]
    labels = ["0-5 MW", "5-10 MW", "10-20 MW", "20-40 MW", "40-80 MW", "80+ MW"]

    if viirs_df is None or viirs_df.empty:
        return pd.DataFrame(columns=["frp_bin", "total_viirs", "matched_modis", "lower_bound_rate_pct"])

    v_work = viirs_df.copy()
    v_work["matched_by_modis"] = False

    if modis_df is not None and not modis_df.empty:
        sat_upper = modis_df["satellite"].astype(str).str.upper()
        is_terra = sat_upper.str.contains("TERRA") | (sat_upper == "T")
        m_work = modis_df if include_terra else modis_df[~is_terra]

        m_groups = {dt: grp for dt, grp in m_work.groupby("date_str")}
        matched_flags = np.zeros(len(v_work), dtype=bool)

        for dt_str, v_grp in v_work.groupby("date_str"):
            m_grp = m_groups.get(dt_str)
            if m_grp is None or m_grp.empty:
                continue

            v_lats = v_grp["latitude"].to_numpy()
            v_lons = v_grp["longitude"].to_numpy()
            v_times = (v_grp["datetime"].astype("int64") // 10**9).to_numpy() / 60.0

            m_lats = m_grp["latitude"].to_numpy()
            m_lons = m_grp["longitude"].to_numpy()
            m_times = (m_grp["datetime"].astype("int64") // 10**9).to_numpy() / 60.0

            dist_mat = _haversine_matrix_km(v_lats, v_lons, m_lats, m_lons)
            time_mat = np.abs(m_times[None, :] - v_times[:, None])
            hit = ((dist_mat <= max_dist_km) & (time_mat <= max_time_min)).any(axis=1)
            matched_flags[v_grp.index.to_numpy()] = hit

        v_work["matched_by_modis"] = matched_flags

    v_work["frp_bin"] = pd.cut(v_work["frp"].clip(lower=0.01), bins=bins, labels=labels, include_lowest=True)
    grp = v_work.groupby("frp_bin", observed=False).agg(
        total_viirs=("frp", "count"),
        matched_modis=("matched_by_modis", "sum")
    ).reset_index()

    grp["matched_modis"] = grp["matched_modis"].astype(int)
    grp["lower_bound_rate_pct"] = np.where(
        grp["total_viirs"] > 0,
        np.round(100.0 * grp["matched_modis"] / grp["total_viirs"], 1),
        0.0
    )
    return grp


def calibrate_frp_time_block(pairs_df):
    """Zaman-bloklu (Time-Block Split) log-FRP kalibrasyonu ve bağımsız test MAE hesabı."""
    metrics = {
        "calibrated": False,
        "train_samples": 0,
        "test_samples": 0,
        "raw_mae_mw": 0.0,
        "calibrated_mae_mw": 0.0,
        "better_than_raw": False
    }

    if pairs_df is None or len(pairs_df) < 12:
        return None, metrics

    ordered = pairs_df.sort_values("date_str").reset_index(drop=True)
    split_idx = int(len(ordered) * 0.75)
    split_idx = max(min(split_idx, len(ordered) - 3), 6)

    train_df = ordered.iloc[:split_idx]
    test_df = ordered.iloc[split_idx:]

    x_train = np.log1p(train_df[["viirs_frp_sum"]].to_numpy())
    y_train = np.log1p(train_df["aqua_frp"].to_numpy())

    x_test = np.log1p(test_df[["viirs_frp_sum"]].to_numpy())
    y_test_true = test_df["aqua_frp"].to_numpy()
    y_test_raw = test_df["viirs_frp_sum"].to_numpy()

    try:
        model = HuberRegressor(max_iter=200).fit(x_train, y_train)
    except Exception:
        model = Ridge(alpha=1.0).fit(x_train, y_train)

    y_pred = np.expm1(model.predict(x_test))
    raw_mae = float(np.mean(np.abs(y_test_true - y_test_raw)))
    cal_mae = float(np.mean(np.abs(y_test_true - y_pred)))

    metrics.update({
        "calibrated": True,
        "train_samples": int(len(train_df)),
        "test_samples": int(len(test_df)),
        "raw_mae_mw": round(raw_mae, 2),
        "calibrated_mae_mw": round(cal_mae, 2),
        "better_than_raw": bool(cal_mae <= raw_mae)
    })
    return model, metrics


def analyze_static_and_recurring_sites(modis_df):
    """1 km Grid (~0.01 derece) bazında tekrarlayan termal noktaları ve NASA Type=2 kaynaklarını toplar."""
    if modis_df is None or modis_df.empty:
        return pd.DataFrame()

    d = modis_df.copy()
    d["lat_grid"] = d["latitude"].round(2)
    d["lon_grid"] = d["longitude"].round(2)
    d["site_grid"] = d["lat_grid"].map(lambda x: f"{x:.2f}N") + "_" + d["lon_grid"].map(lambda x: f"{x:.2f}E")
    d["is_type2"] = (d["type"] == 2)

    agg = d.groupby("site_grid", as_index=False).agg(
        center_lat=("latitude", "mean"),
        center_lon=("longitude", "mean"),
        total_detections=("frp", "count"),
        distinct_days=("date_str", "nunique"),
        distinct_months=("month", "nunique"),
        mean_frp_mw=("frp", "mean"),
        has_nasa_type2=("is_type2", "any"),
        type2_record_count=("is_type2", "sum")
    )

    candidates = agg[(agg["distinct_days"] >= 2) | (agg["has_nasa_type2"])].copy()
    candidates["type2_record_count"] = candidates["type2_record_count"].astype(int)
    return candidates.sort_values(
        by=["has_nasa_type2", "distinct_days", "total_detections"],
        ascending=[False, False, False]
    ).reset_index(drop=True)