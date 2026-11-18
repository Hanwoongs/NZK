"""Build Ref_IS without changing Ref or the selected MacroEnergy package.

All added economic and process values are declared synthetic placeholders.
Only files owned by the previous generated manifest may be replaced or removed.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json

HERE = Path(__file__).resolve().parent
CASE_ROOT = HERE.parent.parent

def baseline_bytes(path):
    # Git checkouts can use CRLF or LF. Model data are text; normalize only CRLF.
    return path.read_bytes().replace(b"\r\n", b"\n")

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def asset_id(key, region):
    return f"steel_{key}_{region}"

def edge(commodity, node, incoming=True):
    return {"commodity": commodity, "unidirectional": True, "has_capacity": False,
            "start_vertex" if incoming else "end_vertex": node}

def supply(commodity, node_id, price, upper=float("inf")):
    return {"type": commodity, "global_data": {"time_interval": commodity,
            "constraints": {"BalanceConstraint": True}}, "instance_data": [{
                "id": node_id, "supply": {"segment1": {"price": [price], "min": [0.0], "max": [upper]}}}]}

def custom_sources(source):
    files = {}
    names = [("integratedblastfurnacebasicoxygenfurnace.jl", "BlastFurnaceBasicOxygenFurnace", "BFBOFSteel"),
             ("integratedblastfurnacebasicoxygenfurnaceccs.jl", "BlastFurnaceBasicOxygenFurnaceCCS", "BFBOFSteel_CCS")]
    for filename, original, custom in names:
        text = (source / "src/model/assets" / filename).read_text(encoding="utf-8-sig")
        text = text.replace(original, custom)
        if custom == "BFBOFSteel":
            text = text.replace("electricity_production", "electricity_consumption")
            start = text.index("    elec_start_node = bfbof_transform")
            stop = text.index("    elec_edge = Edge(", start)
            text = text[:start] + '''    @start_vertex(
        elec_start_node,
        elec_edge_data,
        Electricity,
        [(elec_edge_data, :start_vertex), (data, :location)],
    )
    elec_end_node = bfbof_transform
''' + text[stop:]
        header = ("# Ref_IS custom asset derived from the selected standard rc1 asset.\n"
                  "# The MacroEnergy constraint library is unchanged.\n")
        files[f"user_additions/assets/{custom}.jl"] = (header + text).encode("utf-8")
    return files

def steel_group(tech, year, cfg):
    key = tech["key"]
    active_targets = {t["key"] for t in cfg["technologies"] if t["first_year"] <= year}
    retrofit_specs = [r for r in tech.get("retrofits", []) if r["target"] in active_targets]
    cap = {"commodity": "CrudeSteel", "has_capacity": True, "unidirectional": True,
           "can_expand": True, "can_retire": True, "integer_decisions": False,
           "investment_cost": tech["investment_cost"], "fixed_om_cost": tech["fixed_om_cost"],
           "variable_om_cost": 0.0, "wacc": cfg["wacc"], "lifetime": cfg["steel_lifetime_years"],
           "capital_recovery_period": cfg["steel_capital_recovery_years"],
           "constraints": {"CapacityConstraint": True, "MinFlowConstraint": True, "RampingLimitConstraint": True},
           "min_flow_fraction": cfg["min_flow_fraction"], "ramp_up_fraction": cfg["ramp_up_fraction"],
           "ramp_down_fraction": cfg["ramp_down_fraction"]}
    instances = []
    for region in cfg["regions"]:
        output = {"end_vertex": f"crudesteel_{region}",
                  "existing_capacity": tech["existing_capacity_2021_t_per_h"] if year == 2021 else 0.0,
                  "can_retrofit": bool(retrofit_specs)}
        edges = {"crudesteel_edge": output,
                 "elec_edge": edge("Electricity", f"elec_{region}"),
                 "co2_edge": edge("CO2", "co2_sink_KR", False)}
        if key.startswith("bfbof"):
            edges.update({"ironore_edge": edge("IronOre", "ironore_source"),
                          "steelscrap_edge": edge("SteelScrap", "steelscrap_source"),
                          "metcoal_edge": edge("Coal", "coal_source"),
                          "thermalcoal_edge": edge("Coal", "coal_source"),
                          "natgas_edge": edge("NaturalGas", "natgas_source")})
        elif "dri_eaf" in key:
            hydrogen = key == "h2_dri_eaf"
            edges.update({"ironore_edge": edge("IronOre", "ironore_source"),
                          "reductant_edge": edge("Hydrogen" if hydrogen else "NaturalGas",
                                                 f"h2_{region}" if hydrogen else "natgas_source")})
            if key != "ng_dri_eaf_ccs":
                edges["carbonsource_edge"] = edge("Coal", "coal_source")
        else:
            edges.update({"steelscrap_edge": edge("SteelScrap", "steelscrap_source"),
                          "naturalgas_edge": edge("NaturalGas", "natgas_source"),
                          "carbonsource_edge": edge("Coal", "coal_source")})
        if key.endswith("_ccs"):
            edges["co2_captured_edge"] = edge("CO2Captured", "co2_captured_KR", False)
        instance = {"id": asset_id(key, region), "location": region, "edges": edges}
        if retrofit_specs:
            instance["retrofit_options"] = [{
                "template_id": asset_id(r["target"], region),
                "id": asset_id(r["target"], region) + "_retrofit",
                "edges": {"crudesteel_edge": {"is_retrofit": True, "can_expand": True,
                          "existing_capacity": 0.0, "retrofit_efficiency": 1.0,
                          "investment_cost": r["investment_cost"]}}} for r in retrofit_specs]
        instances.append(instance)
    return {"type": tech["type"], "global_data": {
        "transforms": {"timedata": "CrudeSteel", "constraints": {"BalanceConstraint": True}, **tech["transforms"]},
        "edges": {"crudesteel_edge": cap}}, "instance_data": instances}

def electrolyzer_group(cfg):
    values = cfg["electrolyzer"]
    cap = {"commodity": "Hydrogen", "has_capacity": True, "unidirectional": True,
           "can_expand": True, "can_retire": True, "existing_capacity": 0.0,
           "constraints": {"CapacityConstraint": True}, "wacc": cfg["wacc"],
           **{key: value for key, value in values.items() if key != "efficiency_rate"}}
    return {"type": "Electrolyzer", "global_data": {
        "transforms": {"timedata": "Electricity", "constraints": {"BalanceConstraint": True},
                       "efficiency_rate": values["efficiency_rate"]}, "edges": {"h2_edge": cap}},
        "instance_data": [{"id": f"electrolyzer_steel_{region}", "location": region,
            "edges": {"h2_edge": {"end_vertex": f"h2_{region}"},
                      "elec_edge": edge("Electricity", f"elec_{region}")}} for region in cfg["regions"]]}

def plan_files(cfg):
    parent = CASE_ROOT
    baseline = parent / cfg["baseline_case"]
    source = (parent / cfg["source_root"]).resolve()
    files = {}
    for directory in ["assets", "system", "settings"]:
        for path in sorted((baseline / directory).rglob("*")):
            if path.is_file():
                files[path.relative_to(baseline).as_posix()] = baseline_bytes(path)
    for name in ["system_data.json"]:
        if (baseline / name).is_file():
            files[name] = baseline_bytes(baseline / name)
    baseline_hashes = {path: sha(data) for path, data in files.items()}
    settings = read_json(baseline / "settings/macro_settings.json")
    settings["Retrofitting"] = True
    files["settings/macro_settings.json"] = encoded(settings)
    commodities = read_json(baseline / "system/commodities.json")
    for item in ["Hydrogen", "IronOre", "SteelScrap", "CrudeSteel"]:
        if item not in commodities["commodities"]:
            commodities["commodities"].append(item)
    files["system/commodities.json"] = encoded(commodities)
    time_data = read_json(baseline / "system/time_data.json")
    for commodity in ["Hydrogen", "IronOre", "SteelScrap", "CrudeSteel"]:
        time_data["HoursPerTimeStep"][commodity] = 1
        time_data["HoursPerSubperiod"][commodity] = 8760
    files["system/time_data.json"] = encoded(time_data)
    inventory = []
    for year in cfg["years"]:
        nodes = read_json(baseline / f"system/nodes_{year}.json")
        nodes["nodes"].extend([
            supply("IronOre", "ironore_source", cfg["ironore_price_per_t"]),
            supply("SteelScrap", "steelscrap_source", cfg["scrap_price_per_t"], cfg["annual_national_scrap_limit_t"] / 8760),
            {"type": "Hydrogen", "global_data": {"time_interval": "Hydrogen", "constraints": {"BalanceConstraint": True}},
             "instance_data": [{"id": f"h2_{r}"} for r in cfg["regions"]]},
            {"type": "CrudeSteel", "global_data": {"time_interval": "CrudeSteel",
             "constraints": {"BalanceConstraint": False, "AggregatedDemandConstraint": True}},
             "instance_data": [{"id": f"crudesteel_{r}", "rhs_policy": {
                 "AggregatedDemandConstraint": cfg["annual_steel_demand_per_region_t"]}} for r in cfg["regions"]]}
        ])
        files[f"system/nodes_{year}.json"] = encoded(nodes)
        for tech in cfg["technologies"]:
            if tech["first_year"] > year:
                continue
            # Retrofit templates must load before their source assets in rc1.
            suffix = "_retrofit_option" if tech["key"] in ("bfbof_ccs", "ng_dri_eaf_ccs", "h2_dri_eaf") else ""
            filename = f"assets/assets_{year}/steel_{tech['key']}{suffix}.json"
            group = steel_group(tech, year, cfg)
            files[filename] = encoded({"steel_" + tech["key"]: [group]})
            inventory.extend({"year": year, "id": item["id"], "type": tech["type"], "file": filename,
                              "retrofit_targets": [r["template_id"] for r in item.get("retrofit_options", [])]}
                             for item in group["instance_data"])
        files[f"assets/assets_{year}/electrolyzer_steel.json"] = encoded({"electrolyzer_steel": [electrolyzer_group(cfg)]})
    files.update(custom_sources(source))
    provenance = {"baseline": cfg["baseline_case"], "source": cfg["source_root"], "parameter_status": cfg["parameter_status"],
        "configuration_sha256": sha((HERE / "config.json").read_bytes()),
        "baseline_hashes": baseline_hashes,
        "source_hashes": {p.relative_to(source).as_posix(): sha(p.read_bytes()) for p in sorted((source / "src").rglob("*.jl"))},
        "steel_inventory": inventory, "generated_files": {path: sha(data) for path, data in files.items()}}
    return files, provenance

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify reproducibility without writing files")
    args = parser.parse_args()
    cfg = read_json(HERE / "config.json")
    target = (CASE_ROOT / cfg["output_case"]).resolve()
    baseline = (CASE_ROOT / cfg["baseline_case"]).resolve()
    if target == baseline or target != CASE_ROOT.resolve():
        raise ValueError("The output must be this Ref_IS directory, separate from the Ref baseline")
    files, provenance = plan_files(cfg)
    manifest_path = target / "auxiliary/template_manifest.json"
    previous = read_json(manifest_path).get("generated_files", {}) if manifest_path.exists() else {}
    differences = []
    for relative, data in files.items():
        path = target / relative
        if not path.exists() or path.read_bytes() != data:
            differences.append(relative)
        if not args.check and path.exists() and path.read_bytes() != data and sha(path.read_bytes()) != previous.get(relative):
            raise RuntimeError(f"Untracked/user-modified output will not be overwritten: {path}")
    obsolete = set(previous) - set(files)
    if args.check:
        if differences or obsolete or not manifest_path.exists() or read_json(manifest_path) != provenance:
            raise RuntimeError(f"Generated case differs: {differences}; obsolete: {sorted(obsolete)}")
        print("PASS: Ref_IS is reproducible from the recorded Ref and template configuration")
        return
    for relative in obsolete:
        path = (target / relative).resolve()
        if not path.is_relative_to(target) or (path.exists() and sha(path.read_bytes()) != previous[relative]):
            raise RuntimeError(f"Refusing removal of changed/outside output: {path}")
    for relative, data in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    for relative in obsolete:
        (target / relative).unlink(missing_ok=True)
    manifest_path.write_bytes(encoded(provenance))
    print(f"Built {target}; {len(files)} input/document files; {len(provenance['steel_inventory'])} steel records")

if __name__ == "__main__":
    main()
