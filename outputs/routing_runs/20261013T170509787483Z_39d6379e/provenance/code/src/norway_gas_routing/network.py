"""Inspect and validate ordinary YAML network dictionaries."""

from .validation import ValidationError, check_choice, check_identifier, check_keys, nonnegative_number


def reachable_markets(model: dict, source: str) -> tuple[str, ...]:
    """Return reachable destinations, not optimal routes or volumes."""
    if source not in model["sources"] or not model["sources"][source].get("active", True):
        return ()
    reached, pending = {source}, [source]
    while pending:
        node = pending.pop()
        for arc in model["arcs"]:
            if arc.get("active", True) and arc["from"] == node and arc["to"] not in reached:
                reached.add(arc["to"])
                pending.append(arc["to"])
    return tuple(sorted(reached.intersection(model["markets"])))


def validate_sources(sources: dict, series):
    assigned = set()
    for source, entry in sources.items():
        check_keys(entry, source, {"series", "status"}, {"active", "notes"})
        check_choice(entry["status"], {"ACCEPTED", "PROPOSED", "REVIEW", "TODO"}, f"{source}.status")
        if not isinstance(entry["series"], list):
            raise ValidationError(f"{source}.series must be a list")
        if entry.get("active", True) and (not entry["series"] or source == "OTHER_RESIDUAL"):
            raise ValidationError(f"Source {source} must remain inactive until supply is resolved")
        for ref in entry["series"]:
            if not isinstance(ref, str) or ref not in series.index:
                raise ValidationError(f"Unknown production series for {source}: {ref}")
            if ref in assigned:
                raise ValidationError(f"Production series mapped more than once: {ref}")
            if series.at[ref, "category"] != "production" or series.at[ref, "model_role"] not in {"supply", "residual_calculation"}:
                raise ValidationError(f"Not component production supply: {ref}")
            assigned.add(ref)


def validate_assets(assets: dict, series):
    for name, asset in assets.items():
        check_identifier(name, "assets", uppercase=True)
        check_keys(asset, name, {"type", "technical_capacity_mcm_d"},
                   {"availability_series", "maintenance_series", "priority", "active", "status", "notes"})
        check_choice(asset["type"], {"source_capacity", "route_capacity", "export_corridor", "exit_capacity", "direct"}, f"{name}.type")
        if type(asset.get("active", True)) is not bool:
            raise ValidationError(f"{name}.active must be a boolean")
        if asset["technical_capacity_mcm_d"] is not None:
            nonnegative_number(asset["technical_capacity_mcm_d"], f"{name}.technical_capacity_mcm_d")
        if asset.get("availability_series") and asset.get("maintenance_series"):
            raise ValidationError(f"Overlapping capacity inputs for {name}")
        for field in ("availability_series", "maintenance_series"):
            ref = asset.get(field)
            if ref is not None and (not isinstance(ref, str) or ref not in series.index or series.at[ref, "category"] != "maintenance_capacity"):
                raise ValidationError(f"Invalid {field} reference for {name}: {ref}")


def validate_arcs(model: dict, nodes: set, inactive: set):
    if not isinstance(model["arcs"], list):
        raise ValidationError("arcs must be a list")
    seen, origins = set(), set()
    for arc in model["arcs"]:
        check_keys(arc, "arc", {"id", "from", "to", "asset"}, {"active", "physical_exit"})
        name = arc["id"]
        check_identifier(name, "arc.id", uppercase=True)
        if name in seen:
            raise ValidationError(f"Duplicate arc identifier: {name}")
        seen.add(name)
        for side in ("from", "to"):
            check_identifier(arc[side], f"{name}.{side}", uppercase=True)
            if arc[side] not in nodes:
                raise ValidationError(f"Invalid node reference for {name}: {arc[side]}")
        asset = arc["asset"]
        if asset is not None and (not isinstance(asset, str) or asset not in model["assets"]):
            raise ValidationError(f"Invalid asset reference for {name}: {asset}")
        if type(arc.get("active", True)) is not bool:
            raise ValidationError(f"{name}.active must be a boolean")
        if arc.get("active", True):
            if arc["from"] in inactive or arc["to"] in inactive or (asset and not model["assets"][asset].get("active", True)):
                raise ValidationError(f"Active arc references inactive node/asset: {name}")
            origins.add(arc["from"])
        if arc["from"] == arc["to"] or arc["from"] in model["markets"] or arc["to"] in model["sources"]:
            raise ValidationError(f"Invalid routing direction for {name}")
        if arc.get("physical_exit") is not None:
            check_identifier(arc["physical_exit"], name, uppercase=True)
    for source in model["sources"]:
        if source not in inactive and source not in origins:
            raise ValidationError(f"Active source has no route: {source}")


def validate_network(model: dict, series):
    nodes, inactive = set(), set()
    for section in ("sources", "junctions", "markets"):
        for name, entry in model[section].items():
            check_identifier(name, section, uppercase=True)
            if name in nodes:
                raise ValidationError(f"Duplicate node identifier: {name}")
            nodes.add(name)
            if not isinstance(entry, dict) or type(entry.get("active", True)) is not bool:
                raise ValidationError(f"Invalid {section} entry: {name}")
            if not entry.get("active", True):
                inactive.add(name)
    for name, entry in model["junctions"].items():
        check_keys(entry, name, {"description"}, {"aggregate_capacity"})
        if entry.get("aggregate_capacity") is not None:
            raise ValidationError(f"No independent junction capacity is agreed: {name}")
    validate_sources(model["sources"], series)
    validate_assets(model["assets"], series)
    validate_arcs(model, nodes, inactive)
