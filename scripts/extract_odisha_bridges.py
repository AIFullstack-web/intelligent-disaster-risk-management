from pathlib import Path
import json
from datetime import datetime, timezone

import osmium
import geopandas as gpd
from shapely.geometry import LineString, box

PBF_FILE = Path("data/external/osm/eastern-zone-latest.osm.pbf")
OUT_DIR = Path("data/processed")
CSV_FILE = OUT_DIR / "odisha_bridge_inventory.csv"
GEOJSON_FILE = OUT_DIR / "odisha_bridge_inventory.geojson"
META_FILE = OUT_DIR / "odisha_bridge_inventory_metadata.json"

ODISHA_BBOX = (81.30, 17.70, 87.60, 22.60)
STUDY_AREA = box(*ODISHA_BBOX)


class BridgeHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.records = []

    def way(self, w):
        bridge = w.tags.get("bridge")
        if not bridge:
            return

        coords = []

        for node in w.nodes:
            if not node.location.valid():
                return
            coords.append((node.location.lon, node.location.lat))

        if len(coords) < 2:
            return

        geometry = LineString(coords)

        if not geometry.intersects(STUDY_AREA):
            return

        self.records.append(
            {
                "asset_id": f"OSM_way_{w.id}",
                "osm_id": int(w.id),
                "bridge": bridge,
                "highway": w.tags.get("highway"),
                "name": w.tags.get("name"),
                "ref": w.tags.get("ref"),
                "lanes": w.tags.get("lanes"),
                "surface": w.tags.get("surface"),
                "layer": w.tags.get("layer"),
                "oneway": w.tags.get("oneway"),
                "maxweight": w.tags.get("maxweight"),
                "geometry": geometry,
            }
        )


def main():
    if not PBF_FILE.exists():
        raise FileNotFoundError(f"PBF not found: {PBF_FILE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Reading:", PBF_FILE)
    print("Extracting bridge ways inside Odisha study area...")

    handler = BridgeHandler()
    handler.apply_file(str(PBF_FILE), locations=True)

    gdf = gpd.GeoDataFrame(
        handler.records,
        geometry="geometry",
        crs="EPSG:4326",
    )

    if gdf.empty:
        print("No bridge ways found.")
        return

    gdf = gdf.drop_duplicates(subset=["osm_id"]).reset_index(drop=True)

    gdf["longitude"] = gdf.geometry.centroid.x
    gdf["latitude"] = gdf.geometry.centroid.y

    metric = gdf.to_crs(32644)
    gdf["length_m"] = metric.geometry.length.round(2)

    gdf["geometry_valid"] = gdf.geometry.is_valid

    gdf["name"] = gdf["name"].fillna("Unnamed bridge")
    gdf["highway"] = gdf["highway"].fillna("unknown")

    gdf["source"] = "Geofabrik Eastern India OSM extract"

    csv_gdf = gdf.copy()
    csv_gdf["geometry_wkt"] = csv_gdf.geometry.to_wkt()

    csv_cols = [
        "asset_id",
        "osm_id",
        "bridge",
        "highway",
        "name",
        "ref",
        "lanes",
        "surface",
        "layer",
        "oneway",
        "maxweight",
        "longitude",
        "latitude",
        "length_m",
        "geometry_valid",
        "source",
        "geometry_wkt",
    ]

    csv_gdf[csv_cols].to_csv(CSV_FILE, index=False)

    gdf.to_file(GEOJSON_FILE, driver="GeoJSON")

    metadata = {
        "source_file": str(PBF_FILE).replace("\\", "/"),
        "source": "Geofabrik Eastern India OSM extract",
        "study_bbox": ODISHA_BBOX,
        "crs": "EPSG:4326",
        "asset_type": "OSM bridge-tagged ways",
        "records": len(gdf),
        "unique_osm_ids": int(gdf["osm_id"].nunique()),
        "valid_geometries": int(gdf["geometry_valid"].sum()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    META_FILE.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print()
    print("ODISHA BRIDGE EXTRACTION COMPLETE")
    print("BRIDGE ASSETS:", len(gdf))
    print("UNIQUE OSM IDS:", gdf["osm_id"].nunique())
    print("VALID GEOMETRIES:", int(gdf["geometry_valid"].sum()))
    print("UNKNOWN HIGHWAY:", int((gdf["highway"] == "unknown").sum()))
    print("NAMED BRIDGES:", int((gdf["name"] != "Unnamed bridge").sum()))
    print("CSV:", CSV_FILE)
    print("GEOJSON:", GEOJSON_FILE)
    print("METADATA:", META_FILE)


if __name__ == "__main__":
    main()
