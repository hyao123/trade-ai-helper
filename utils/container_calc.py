"""
utils/container_calc.py
-----------------------
Container loading calculator for international trade.

Supports standard container types:
- 20GP (20ft General Purpose)
- 40GP (40ft General Purpose)
- 40HQ (40ft High Cube)

Calculates:
- How many cartons fit in a container (floor-loading & stacking)
- Volume utilization percentage
- Weight utilization percentage
- Optimal loading arrangement
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger("container_calc")

# ---------------------------------------------------------------------------
# Container Specifications (internal dimensions in mm, max payload in kg)
# ---------------------------------------------------------------------------
CONTAINER_SPECS: dict[str, dict] = {
    "20GP": {
        "name": "20' General Purpose",
        "length_mm": 5898,
        "width_mm": 2352,
        "height_mm": 2393,
        "max_payload_kg": 21770,
        "tare_weight_kg": 2230,
        "cbm": 33.2,
    },
    "40GP": {
        "name": "40' General Purpose",
        "length_mm": 12032,
        "width_mm": 2352,
        "height_mm": 2393,
        "max_payload_kg": 26680,
        "tare_weight_kg": 3740,
        "cbm": 67.7,
    },
    "40HQ": {
        "name": "40' High Cube",
        "length_mm": 12032,
        "width_mm": 2352,
        "height_mm": 2698,
        "max_payload_kg": 26460,
        "tare_weight_kg": 3940,
        "cbm": 76.3,
    },
}


@dataclass
class CartonSpec:
    """Carton dimensions and weight specification."""
    length_mm: float
    width_mm: float
    height_mm: float
    gross_weight_kg: float
    quantity_per_carton: int = 1
    stackable: bool = True
    max_stack_layers: int = 10


@dataclass
class LoadingResult:
    """Result of container loading calculation."""
    container_type: str
    container_name: str
    cartons_per_layer: int
    layers: int
    total_cartons: int
    total_units: int
    total_weight_kg: float
    volume_used_cbm: float
    volume_total_cbm: float
    volume_utilization_pct: float
    weight_utilization_pct: float
    arrangement: str  # e.g. "L x W per layer"
    length_fit: int
    width_fit: int
    remaining_space_mm: dict  # leftover in each dimension
    warnings: list[str]


def _try_orientations(
    carton: CartonSpec,
    container_l: float,
    container_w: float,
    container_h: float,
    max_payload_kg: float,
) -> LoadingResult | None:
    """
    Try all 3 carton orientations (rotating L/W/H) and return the best loading result.
    """
    dims = [carton.length_mm, carton.width_mm, carton.height_mm]
    # Generate all 3 unique orientations (which dimension faces up)
    orientations = [
        (dims[0], dims[1], dims[2]),  # normal: L x W, H up
        (dims[0], dims[2], dims[1]),  # rotate: L x H, W up
        (dims[1], dims[2], dims[0]),  # rotate: W x H, L up
    ]

    best: LoadingResult | None = None

    for cl, cw, ch in orientations:
        # How many cartons fit along each container dimension
        fit_l = int(container_l // cl)
        fit_w = int(container_w // cw)
        fit_h = int(container_h // ch)

        if fit_l == 0 or fit_w == 0 or fit_h == 0:
            continue

        # Apply stacking limit
        if carton.stackable:
            fit_h = min(fit_h, carton.max_stack_layers)
        else:
            fit_h = 1

        cartons_per_layer = fit_l * fit_w
        total_cartons = cartons_per_layer * fit_h
        total_weight = total_cartons * carton.gross_weight_kg

        # Weight constraint
        if total_weight > max_payload_kg:
            # Reduce cartons to fit weight
            max_cartons_by_weight = int(max_payload_kg / carton.gross_weight_kg)
            layers_by_weight = max_cartons_by_weight // cartons_per_layer
            if layers_by_weight == 0:
                layers_by_weight = 1
                cartons_per_layer_adj = max_cartons_by_weight
                total_cartons = cartons_per_layer_adj
            else:
                fit_h = layers_by_weight
                total_cartons = cartons_per_layer * fit_h
            total_weight = total_cartons * carton.gross_weight_kg

        # Volume calculations
        carton_vol_cbm = (cl * cw * ch) / 1_000_000_000
        volume_used = total_cartons * carton_vol_cbm
        volume_total = (container_l * container_w * container_h) / 1_000_000_000

        if best is None or total_cartons > best.total_cartons:
            warnings = []
            weight_util = (total_weight / max_payload_kg) * 100
            vol_util = (volume_used / volume_total) * 100

            if weight_util > 95:
                warnings.append("Weight near maximum payload limit")
            if vol_util < 50:
                warnings.append("Low volume utilization - consider smaller container")

            best = LoadingResult(
                container_type="",  # filled by caller
                container_name="",
                cartons_per_layer=cartons_per_layer,
                layers=fit_h,
                total_cartons=total_cartons,
                total_units=total_cartons * carton.quantity_per_carton,
                total_weight_kg=round(total_weight, 2),
                volume_used_cbm=round(volume_used, 3),
                volume_total_cbm=round(volume_total, 1),
                volume_utilization_pct=round(vol_util, 1),
                weight_utilization_pct=round(weight_util, 1),
                arrangement=f"{fit_l} x {fit_w} per layer, {fit_h} layers",
                length_fit=fit_l,
                width_fit=fit_w,
                remaining_space_mm={
                    "length": round(container_l - fit_l * cl, 1),
                    "width": round(container_w - fit_w * cw, 1),
                    "height": round(container_h - fit_h * ch, 1),
                },
                warnings=warnings,
            )

    return best


def calculate_loading(
    carton: CartonSpec,
    container_type: str = "40HQ",
) -> LoadingResult | None:
    """
    Calculate how many cartons fit in the specified container.

    Args:
        carton: CartonSpec with dimensions and weight
        container_type: One of '20GP', '40GP', '40HQ'

    Returns:
        LoadingResult with detailed breakdown, or None if carton doesn't fit.
    """
    spec = CONTAINER_SPECS.get(container_type)
    if not spec:
        logger.error("Unknown container type: %s", container_type)
        return None

    logger.info(
        "Calculating loading: carton=%dx%dx%d mm, weight=%.1f kg, container=%s",
        carton.length_mm, carton.width_mm, carton.height_mm,
        carton.gross_weight_kg, container_type,
    )

    result = _try_orientations(
        carton,
        spec["length_mm"],
        spec["width_mm"],
        spec["height_mm"],
        spec["max_payload_kg"],
    )

    if result:
        result.container_type = container_type
        result.container_name = spec["name"]
        logger.info("Loading result: %d cartons, %.1f%% volume, %.1f%% weight",
                    result.total_cartons, result.volume_utilization_pct, result.weight_utilization_pct)
    else:
        logger.warning("Carton too large for container %s", container_type)

    return result


def calculate_all_containers(carton: CartonSpec) -> list[LoadingResult]:
    """
    Calculate loading for all container types and return sorted results.

    Returns list of LoadingResult sorted by total_cartons descending.
    """
    results = []
    for ct in CONTAINER_SPECS:
        r = calculate_loading(carton, ct)
        if r:
            results.append(r)
    results.sort(key=lambda x: x.total_cartons, reverse=True)
    return results


def recommend_container(
    carton: CartonSpec,
    target_quantity: int,
) -> dict:
    """
    Recommend the best container type for a target quantity of cartons.

    Returns dict with:
    - recommended: str (container type)
    - containers_needed: int
    - details: LoadingResult for the recommended container
    - all_options: list of dicts with container options
    """
    all_results = calculate_all_containers(carton)
    if not all_results:
        return {"recommended": None, "containers_needed": 0, "details": None, "all_options": []}

    options = []
    for r in all_results:
        containers_needed = math.ceil(target_quantity / r.total_cartons) if r.total_cartons > 0 else 0
        options.append({
            "container_type": r.container_type,
            "container_name": r.container_name,
            "cartons_per_container": r.total_cartons,
            "containers_needed": containers_needed,
            "total_capacity": r.total_cartons * containers_needed,
            "volume_utilization": r.volume_utilization_pct,
            "weight_utilization": r.weight_utilization_pct,
        })

    # Recommend the one needing fewest containers (prefer HQ for equal count)
    options.sort(key=lambda x: (x["containers_needed"], -x["volume_utilization"]))
    best = options[0]

    return {
        "recommended": best["container_type"],
        "containers_needed": best["containers_needed"],
        "details": next(r for r in all_results if r.container_type == best["container_type"]),
        "all_options": options,
    }
