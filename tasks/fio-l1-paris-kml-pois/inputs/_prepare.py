"""Authoring-time helper: build the bundled Google-My-Maps style KML.

Slices Overture `theme=places/type=place` over a central-Paris bbox for
three amenity-ish category families (cafe, library, tourist info) and
writes a KML with the structure a Google My Maps export would produce:

  <kml><Document>
    <Folder><name>{category}</name>
       <Placemark>
         <name>{place name}</name>
         <description><![CDATA[<HTML blob>]]></description>
         <Point><coordinates>lon,lat,0</coordinates></Point>
       </Placemark>
       ...
    </Folder>
    ...
  </Document></kml>

The trick the agent has to get right:
  * The *category* is encoded as the parent Folder name, not as a
    Placemark attribute. Naive `gpd.read_file(kml)` returns whatever
    layer pyogrio happens to pick first; the agent has to either iterate
    layers (each Folder is a layer in the KML driver) or parse the XML.
  * The *description* is an HTML blob (`<b>`, `<br>`, `<a>` tags wrapped
    in CDATA). It must be stripped to plain text before writing GeoJSON
    — the persona's downstream map server rejects HTML.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l1-paris-kml-pois/inputs/_prepare.py
"""
from __future__ import annotations

import html
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
OUT = HERE / "paris_late_night_pois.kml"
RELEASE = "2026-04-15.0"

# Central Paris bbox (1er–10e arrondissements, roughly).
XMIN, YMIN, XMAX, YMAX = 2.30, 48.84, 2.40, 48.89

# Three Google-My-Maps "layer" labels the colleague used. The Overture
# place categories that map onto each (rough mapping — Margaux is a
# transport planner, not a taxonomist):
FOLDERS = [
    (
        "Cafés ouverts tard",
        ["cafe", "coffee_shop"],
        20,
    ),
    (
        "Bibliothèques de nuit",
        ["library", "public_library"],
        15,
    ),
    (
        "Tours et infos touristiques",
        ["sightseeing_tour_agency", "tours", "boat_tours"],
        10,
    ),
]


def _description_html(name: str, category_label: str, idx: int) -> str:
    """Build a deterministic HTML blob mimicking a Google My Maps export.

    Mixes `<b>`, `<br/>`, `<a href>`, and entities (`&amp;`, `&eacute;`).
    Includes line breaks and a fake "last verified" line. Wrapped in
    CDATA when written to KML so the XML parser does not fight the
    HTML.
    """
    name_safe = html.escape(name)
    label_safe = html.escape(category_label)
    # Deterministic per-row "verified" date.
    day = (idx * 13) % 28 + 1
    month = (idx * 7) % 12 + 1
    return (
        f"<b>{name_safe}</b><br/>"
        f"Cat&eacute;gorie&nbsp;: {label_safe}<br/>"
        f'<a href="https://example.org/poi/{idx}">Voir la fiche</a><br/>'
        f"Derni&egrave;re v&eacute;rification&nbsp;: 2026-{month:02d}-{day:02d}"
    )


def _kml_escape(text: str) -> str:
    """Escape XML-significant characters for KML element text."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main() -> None:
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

    folders_data: list[tuple[str, list[tuple[str, float, float]]]] = []
    for folder_name, categories, limit in FOLDERS:
        cats_sql = ",".join(f"'{c}'" for c in categories)
        rows = con.execute(
            f"""
            SELECT
                COALESCE(names.primary, '(sans nom)') AS name,
                ST_X(geometry) AS lon,
                ST_Y(geometry) AS lat
            FROM read_parquet(
                's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
                hive_partitioning=1
            )
            WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
              AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
              AND categories.primary IN ({cats_sql})
              AND names.primary IS NOT NULL
            ORDER BY name, lon, lat
            LIMIT {limit}
            """
        ).fetchall()
        print(f"  {folder_name}: {len(rows)} placemarks")
        folders_data.append((folder_name, rows))

    # Write KML by hand to control the exact Folder/Placemark structure.
    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    lines.append("<Document>")
    lines.append("  <name>Late-night POIs (RATP night-bus study)</name>")

    idx_global = 0
    for folder_name, rows in folders_data:
        lines.append("  <Folder>")
        lines.append(f"    <name>{_kml_escape(folder_name)}</name>")
        for name, lon, lat in rows:
            html_desc = _description_html(name, folder_name, idx_global)
            lines.append("    <Placemark>")
            lines.append(f"      <name>{_kml_escape(name)}</name>")
            lines.append(
                f"      <description><![CDATA[{html_desc}]]></description>"
            )
            lines.append("      <Point>")
            lines.append(f"        <coordinates>{lon:.6f},{lat:.6f},0</coordinates>")
            lines.append("      </Point>")
            lines.append("    </Placemark>")
            idx_global += 1
        lines.append("  </Folder>")

    lines.append("</Document>")
    lines.append("</kml>")

    if OUT.exists():
        OUT.unlink()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = sum(len(rows) for _, rows in folders_data)
    print(f"Wrote {total} placemarks across {len(folders_data)} folders → {OUT}")


if __name__ == "__main__":
    main()
