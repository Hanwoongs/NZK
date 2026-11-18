"""Validate the generated template against the agreed integration boundaries."""
from collections import Counter
from pathlib import Path
import json
import build_template as build

HERE = Path(__file__).resolve().parent
CFG = build.read_json(HERE / "config.json")
ROOT = HERE.parent.parent
BASE = ROOT / CFG["baseline_case"]
CASE = ROOT / CFG["output_case"]


def main():
    manifest = build.read_json(CASE / "auxiliary/template_manifest.json")
    for relative, digest in manifest["baseline_hashes"].items():
        assert build.sha(build.baseline_bytes(BASE / relative)) == digest, f"Ref changed: {relative}"
    for relative, digest in manifest["source_hashes"].items():
        assert build.sha((ROOT / CFG["source_root"] / relative).read_bytes()) == digest, f"Source changed: {relative}"
    planned, expected_manifest = build.plan_files(CFG)
    assert manifest == expected_manifest, "Manifest or input provenance changed"
    for relative, content in planned.items():
        assert (CASE / relative).read_bytes() == content, f"Generated file changed: {relative}"

    assert build.read_json(CASE / "system_data.json") == build.read_json(BASE / "system_data.json")
    assert build.read_json(CASE / "settings/case_settings.json") == build.read_json(BASE / "settings/case_settings.json")
    macro = build.read_json(CASE / "settings/macro_settings.json")
    old_macro = build.read_json(BASE / "settings/macro_settings.json")
    assert macro == {**old_macro, "Retrofitting": True}
    timedata = build.read_json(CASE / "system/time_data.json")
    for commodity in ("Electricity", "Hydrogen", "IronOre", "SteelScrap", "CrudeSteel"):
        assert timedata["HoursPerTimeStep"][commodity] == 1
        assert timedata["HoursPerSubperiod"][commodity] == 8760
    for path in (BASE / "assets").rglob("*"):
        if path.is_file():
            assert build.baseline_bytes(path) == (CASE / path.relative_to(BASE)).read_bytes()

    counts = []
    expected_paths = {("bfbof", "bfbof_ccs"), ("ng_dri_eaf", "ng_dri_eaf_ccs"),
                      ("ng_dri_eaf", "h2_dri_eaf")}
    for year in CFG["years"]:
        old_nodes = build.read_json(BASE / f"system/nodes_{year}.json")["nodes"]
        groups = build.read_json(CASE / f"system/nodes_{year}.json")["nodes"]
        assert groups[:len(old_nodes)] == old_nodes, f"Original node data changed in {year}"
        nodes = {i["id"]: (g["type"], i, g.get("global_data", {})) for g in groups for i in g["instance_data"]}
        assert len(nodes) == sum(len(g["instance_data"]) for g in groups)
        scrap = nodes["steelscrap_source"][1]["supply"]["segment1"]
        assert abs(scrap["max"][0] * 8760 - CFG["annual_national_scrap_limit_t"]) < 1e-8
        for region in CFG["regions"]:
            _, node, common = nodes[f"crudesteel_{region}"]
            assert common["constraints"] == {"BalanceConstraint": False, "AggregatedDemandConstraint": True}
            assert node["rhs_policy"]["AggregatedDemandConstraint"] == CFG["annual_steel_demand_per_region_t"]
        assets = {}
        paths = sorted((CASE / f"assets/assets_{year}").glob("*.json"), key=lambda p: ("_retrofit_option" not in p.name, p.name))
        order = {p.name: n for n, p in enumerate(paths)}
        for path in paths:
            for group_list in build.read_json(path).values():
                for group in group_list:
                    for instance in group["instance_data"]:
                        aid = instance["id"]
                        assert aid not in assets, f"Duplicate asset: {aid}"
                        assets[aid] = (instance, group, path.name)
                        for name, local in instance["edges"].items():
                            merged = {**group["global_data"].get("edges", {}).get(name, {}), **local}
                            assert merged.get("unidirectional", True)
                            for endpoint in ("start_vertex", "end_vertex"):
                                if endpoint in merged:
                                    assert merged[endpoint] in nodes, f"Missing node: {aid}.{name}"
                                    assert nodes[merged[endpoint]][0] == merged["commodity"], f"Commodity mismatch: {aid}.{name}"
                        if "dri_eaf" in aid:
                            assert "steelscrap_edge" not in instance["edges"]
                        if "_ccs_" in aid:
                            assert year >= 2030
                            assert instance["edges"]["co2_captured_edge"]["end_vertex"] == "co2_captured_KR"
                        if aid.startswith("steel_"):
                            cap = group["global_data"]["edges"]["crudesteel_edge"]
                            assert cap["can_expand"]
                            assert all(cap["constraints"].get(c) for c in ("CapacityConstraint", "MinFlowConstraint", "RampingLimitConstraint"))
                            assert instance["edges"]["crudesteel_edge"]["existing_capacity"] >= 0
                            if year != 2021:
                                assert instance["edges"]["crudesteel_edge"]["existing_capacity"] == 0
        retrofit_ids = []
        for aid, (instance, group, filename) in assets.items():
            for option in instance.get("retrofit_options", []):
                target, target_group, target_file = assets[option["template_id"]]
                assert order[target_file] < order[filename], f"Retrofit template loads too late: {aid}"
                source_key = aid[6:].rsplit("_", 1)[0]
                target_key = target["id"][6:].rsplit("_", 1)[0]
                assert (source_key, target_key) in expected_paths
                assert target["location"] == instance["location"]
                assert instance["edges"]["crudesteel_edge"]["can_retrofit"]
                assert option["edges"]["crudesteel_edge"]["is_retrofit"]
                retrofit_ids.append(option["id"])
        assert len(set(retrofit_ids)) == len(retrofit_ids)
        assert not (set(retrofit_ids) & set(assets))
        expected_steel = len(CFG["regions"]) * (4 if year < 2030 else 6)
        assert sum(a.startswith("steel_") for a in assets) == expected_steel
        assert len(retrofit_ids) == len(CFG["regions"]) * (1 if year < 2030 else 3)
        assert sum(a.startswith("electrolyzer_steel_") for a in assets) == 17
        counts.append({"year": year, "steel_base_assets": expected_steel,
                       "electrolyzers": 17, "retrofit_options": len(retrofit_ids)})
    result = {"passed": True, "baseline_unchanged": True, "source_unchanged": True,
              "reproducible": True, "hourly_resolution": 8760, "steel_ccs_first_year": 2030,
              "parameter_status": CFG["parameter_status"], "periods": counts}
    (HERE / "reports").mkdir(exist_ok=True)
    (HERE / "reports/static_validation.json").write_bytes(build.encoded(result))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
