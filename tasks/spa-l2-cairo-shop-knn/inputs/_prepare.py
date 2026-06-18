"""Authoring-time helper: build the bundled Cairo shop + anchor GPKG layers.

Slices ~10 500 `places.place` Point rows out of Overture release
2026-04-15.0 over a Cairo bbox, splits them deterministically into
10 000 "shops" and 100 "market anchors", and writes them as a
two-layer GPKG file in EPSG:22992 (Egypt Red Belt — the canonical
metric CRS Mona's consultancy uses for downtown Cairo work).

Real Overture `names.primary` values are *replaced* with synthetic
chain names in the shops layer:

  - 50% of shops belong to one of 8 known chains. Each chain has 3-4
    deliberately-inconsistent transliteration variants — Latin / Arabic
    / casing / whitespace differences — to populate the inventory's
    "Inconsistent attribute values" data-quality axis. A canonical chain
    label is recorded in a private mapping so the grader can verify the
    agent collapses variants of the same chain to a single normalised
    string per chain (the *value* of the canonical string is the
    agent's choice).
  - The remaining 50% are unique-named non-chain shops ("Local Shop
    NNNN") — these never need normalisation and act as filler that any
    reasonable normalisation strategy must leave alone.

The anchors layer carries 100 named target-market locations with
deliberately untidy raw names (extra whitespace, mixed case) so the
agent must apply at least casefold + whitespace-collapse to produce
`anchor_name_normalised`.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l2-cairo-shop-knn/inputs/_prepare.py
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import duckdb
import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
GPKG_OUT = HERE / "cairo_retail.gpkg"
# Chain ground truth lives under reference/ — it's the grader's
# answer key and must NOT be served to agents under test (only `data/`
# is bundled into the task harness).
CHAIN_MAP_OUT = TASK_DIR / "reference" / "_chain_truth.json"
RELEASE = "2026-04-15.0"

# Greater downtown / inner Cairo bbox. Wide enough that Overture returns
# well over 10 500 places.place rows, tight enough that downtown remains
# the centre of mass.
XMIN, YMIN, XMAX, YMAX = 31.20, 29.95, 31.40, 30.15

N_SHOPS = 10_000
N_ANCHORS = 100
SAMPLE_SEED = 20260508
FIXED_GPKG_TIMESTAMP = "2026-05-08T00:00:00.000Z"

# Eight known chains, each with 3-4 transliteration / casing variants.
# All variants of a chain must collapse to one canonical normalised
# form in the agent's output (which form is up to the agent).
CHAIN_VARIANTS: dict[str, list[str]] = {
    "carrefour": ["Carrefour", "carrefour", "Carrefour Egypt", "كارفور"],
    "metro": ["Metro Market", "metro", "Metro Markets", "مترو"],
    "spinneys": ["Spinneys", "spinneys cairo", "Spineys", "سبينيز"],
    "hyperone": ["HyperOne", "Hyper One", "hyperone", "هايبر وان"],
    "oscar": ["Oscar", "Oscar Grand Stores", "OSCAR", "اوسكار"],
    "seoudi": ["Seoudi", "Seoudi Market", "seoudi supermarket", "سعودي"],
    "kheir_zaman": ["Kheir Zaman", "kheir zaman", "Khair Zaman", "خير زمان"],
    "abu_zekry": ["Abu Zekry", "abou zekry", "Abu Zikri", "أبو زكري"],
}

# Anchor names — 100 plausible Cairo target-market locations. Persisted
# here so reruns are deterministic (no Overture name lookup).
ANCHOR_NAMES = [
    "Tahrir Square Plaza", "Zamalek Riverside", "Maadi Corniche",
    "Heliopolis Square", "New Cairo Tagamoa", "Nasr City Hub",
    "Mohandessin Centre", "Garden City Walk", "Dokki Market",
    "Giza Pyramids Gate", "Roxy Square", "Ramses Crossing",
    "Sayeda Zeinab Plaza", "Khan El Khalili Approach",
    "Bab Al Louq Corner", "Korba Quarter", "Manial Riverbank",
    "Shubra North", "Ain Shams Plaza", "Abbasiya Junction",
    "Boulaq Edge", "Garbiya Plaza", "Sakakini Approach",
    "Dar El Salaam", "El Marg Hub", "Helwan Centre",
    "Maasara Crossing", "Tora Edge", "Mokattam Heights",
    "Nozha Promenade", "Sheraton Heliopolis", "Triumph Square",
    "Cleopatra Plaza", "Salah Salem Strip", "Autostrad Corner",
    "El Rehab Gate One", "El Rehab Gate Two", "Madinaty Promenade",
    "Fifth Settlement North", "Fifth Settlement South",
    "American University Gate", "Police Academy Strip",
    "Ring Road North", "Ring Road East", "Ring Road West",
    "City Stars Mall", "Cairo Festival City",
    "Mall of Egypt Gate", "Tagamoa First", "Tagamoa Third",
    "El Mokattam Plateau", "Al Ahly Stadium", "Cairo Stadium",
    "Sharkawi Plaza", "El Obour Hub", "Shoubra Mazallat",
    "Abdeen Palace Edge", "El Hussein Square", "Al Ghouriya Strip",
    "El Mosky Quarter", "Bab Zuweila Approach", "Ataba Square",
    "Opera Square", "Talaat Harb Plaza", "Soliman Pasha Corner",
    "Sherif Street", "Qasr El Nile", "Kasr El Aini Strip",
    "El Sayeda Aisha", "Kobri El Qubba", "Mar Mina Plaza",
    "Saint Fatima Hub", "El Nozha El Gedida", "Rabaa Square",
    "Tagamoa El Saba", "Bahteem Crossing", "El Salam City",
    "Madinet Nasr Eighth Zone", "Madinet Nasr Tenth Zone",
    "El Hadaba El Wosta", "Mokattam Sector One", "Mokattam Sector Six",
    "El Maadi Degla", "Maadi Sarayat", "Maadi Cornish",
    "Old Cairo Babylon", "Coptic Cairo Plaza", "Fustat Park Edge",
    "Manial Bridge", "Embaba Crossing", "Imbaba Airport Strip",
    "Mit Okba Plaza", "El Agouza Riverside", "El Sahel Junction",
    "Rod El Farag Bridge", "Shubra El Kheima Centre",
    "El Sawah Corner", "Demerdash Plaza", "El Demerdash Hospital Edge",
    "Ramses Hilton Plaza",
]
assert len(ANCHOR_NAMES) == N_ANCHORS, len(ANCHOR_NAMES)

# Chains assigned to ~50% of shops; remainder are non-chain "Local Shop"
# rows. Probability is enforced by hashing — chain_share / non_chain_share.
CHAIN_SHARE = 0.5


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
            TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
            REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
        );
        """
    )
    return con


def _stable_hash(s: str, salt: str) -> int:
    return int(hashlib.sha256(f"{salt}|{s}".encode()).hexdigest(), 16)


def fetch_points(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    """Pull Overture places points in the Cairo bbox; return Points only.

    We don't filter by category — the synthetic chain layer is the
    important attribute, not Overture's original taxonomy. We just need
    geographically-realistic Point distributions.
    """
    df = con.execute(
        f"""
        SELECT
            id,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
        """
    ).fetchdf()
    print(f"Fetched {len(df)} place rows from Overture {RELEASE}")
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.geom_type == "Point"].copy()
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)
    return gdf


def split_shops_and_anchors(
    gdf: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Take the first N_SHOPS rows as shops; build N_ANCHORS anchors on
    a synthetic 10×10 grid across the bbox so no anchor coincides with
    a shop coordinate (Overture places routinely collocate dozens of
    POIs at the same lat/lon, which would break knn tiebreaking)."""
    if len(gdf) < N_SHOPS:
        raise RuntimeError(
            f"Overture returned only {len(gdf)} points; need ≥ {N_SHOPS}"
        )
    shops = gdf.iloc[:N_SHOPS].reset_index(drop=True).copy()

    # 10×10 grid of synthetic anchor points evenly spaced in WGS84
    # over the bbox interior (5% inset so anchors stay inside).
    inset_x = (XMAX - XMIN) * 0.05
    inset_y = (YMAX - YMIN) * 0.05
    xs = [
        XMIN + inset_x + i * (XMAX - XMIN - 2 * inset_x) / 9
        for i in range(10)
    ]
    ys = [
        YMIN + inset_y + j * (YMAX - YMIN - 2 * inset_y) / 9
        for j in range(10)
    ]
    from shapely.geometry import Point as _Point
    pts = [_Point(x, y) for y in ys for x in xs]
    anchors = gpd.GeoDataFrame(
        {"id": [f"GRID-{k:03d}" for k in range(N_ANCHORS)]},
        geometry=pts,
        crs="EPSG:4326",
    )
    assert len(anchors) == N_ANCHORS
    return shops, anchors


def assign_shop_names(shops: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    """Mutate `shops` to carry shop_id + raw_name; record chain truth."""
    chain_keys = list(CHAIN_VARIANTS.keys())
    n_chains = len(chain_keys)

    raw_names: list[str] = []
    truth: dict[str, str | None] = {}
    for i, ovid in enumerate(shops["id"].tolist(), start=1):
        shop_id = f"S{i:05d}"
        # First decide chain vs. non-chain based on a hash bucket.
        bucket = _stable_hash(ovid, "chain_select") % 1000
        if bucket < int(1000 * CHAIN_SHARE):
            chain_idx = _stable_hash(ovid, "chain_pick") % n_chains
            chain_key = chain_keys[chain_idx]
            variants = CHAIN_VARIANTS[chain_key]
            variant_idx = _stable_hash(ovid, "variant_pick") % len(variants)
            raw_names.append(variants[variant_idx])
            truth[shop_id] = chain_key
        else:
            raw_names.append(f"Local Shop {i:05d}")
            truth[shop_id] = None
    shops = shops.assign(
        shop_id=[f"S{i:05d}" for i in range(1, len(shops) + 1)],
        raw_name=raw_names,
    )
    shops = shops[["shop_id", "raw_name", "geometry"]]
    return shops, truth


def assign_anchor_names(anchors: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Attach anchor_id + raw anchor_name with mild casing/whitespace junk."""
    raw_names = []
    for i, name in enumerate(ANCHOR_NAMES, start=1):
        # Inject one of three styles of harmless junk per anchor, hashed
        # by index so it's deterministic.
        style = i % 3
        if style == 0:
            raw_names.append(f"  {name}  ")
        elif style == 1:
            raw_names.append(name.upper())
        else:
            raw_names.append(name)
    anchors = anchors.assign(
        anchor_id=[f"M{i:03d}" for i in range(1, len(anchors) + 1)],
        anchor_name=raw_names,
    )
    anchors = anchors[["anchor_id", "anchor_name", "geometry"]]
    return anchors


def _stamp(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "UPDATE gpkg_contents SET last_change = ?", (FIXED_GPKG_TIMESTAMP,)
        )
        con.commit()
    finally:
        con.close()


def main() -> None:
    con = _connect()
    points = fetch_points(con)
    shops_wgs, anchors_wgs = split_shops_and_anchors(points)
    shops_wgs, truth = assign_shop_names(shops_wgs)
    anchors_wgs = assign_anchor_names(anchors_wgs)

    shops = shops_wgs.to_crs("EPSG:22992")
    anchors = anchors_wgs.to_crs("EPSG:22992")

    if GPKG_OUT.exists():
        GPKG_OUT.unlink()
    shops.to_file(GPKG_OUT, layer="shops", driver="GPKG")
    anchors.to_file(GPKG_OUT, layer="anchors", driver="GPKG")
    _stamp(GPKG_OUT)

    CHAIN_MAP_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_MAP_OUT.write_text(
        json.dumps(
            {
                "shop_id_to_chain": truth,
                "chain_keys": list(CHAIN_VARIANTS.keys()),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(shops)} shops + {len(anchors)} anchors → {GPKG_OUT}")
    n_chain = sum(1 for v in truth.values() if v is not None)
    print(f"Chain shops: {n_chain} ({n_chain/len(truth):.0%})")
    print(f"Truth map → {CHAIN_MAP_OUT}")


if __name__ == "__main__":
    main()
