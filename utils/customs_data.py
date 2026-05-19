"""
utils/customs_data.py
---------------------
Customs & international trade data integration.

Provides:
- HS Code lookup and validation (6/8/10 digit)
- Tariff rate queries by country pair
- Trade statistics (import/export volumes)
- Restricted goods / export control checks
- Country-specific import requirements
- Currency-aware duty calculation

Data sources:
- WCO HS Nomenclature (built-in 2-digit chapter reference)
- External APIs when configured:
  - TRADE_DATA_API_KEY → customs data provider (e.g., TradeMap, UN Comtrade)
  - For offline/demo mode: uses built-in reference data

Usage:
    from utils.customs_data import (
        lookup_hs_chapter,
        validate_hs_code,
        get_tariff_info,
        calculate_duty,
        get_trade_stats,
        check_export_controls,
        get_import_requirements,
    )
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import load_json, save_json

logger = get_logger("customs_data")

_CACHE_FILE = "customs_cache.json"
_CACHE_TTL_HOURS = 24 * 7  # Cache for 1 week

# ---------------------------------------------------------------------------
# Built-in HS Chapter reference (2-digit level, WCO 2022)
# ---------------------------------------------------------------------------

HS_CHAPTERS: dict[str, dict[str, str]] = {
    "01": {"en": "Live animals", "zh": "活动物"},
    "02": {"en": "Meat and edible meat offal", "zh": "肉及食用杂碎"},
    "03": {"en": "Fish and crustaceans", "zh": "鱼及甲壳动物"},
    "04": {"en": "Dairy produce; eggs; honey", "zh": "乳品；蛋品；蜂蜜"},
    "07": {"en": "Edible vegetables", "zh": "食用蔬菜"},
    "08": {"en": "Edible fruit and nuts", "zh": "食用水果及坚果"},
    "09": {"en": "Coffee, tea, spices", "zh": "咖啡、茶、香料"},
    "15": {"en": "Animal or vegetable fats and oils", "zh": "动植物油脂"},
    "16": {"en": "Preparations of meat, fish", "zh": "肉、鱼制品"},
    "17": {"en": "Sugars and sugar confectionery", "zh": "糖及糖食"},
    "18": {"en": "Cocoa and cocoa preparations", "zh": "可可及制品"},
    "19": {"en": "Preparations of cereals, flour", "zh": "谷物制品"},
    "20": {"en": "Preparations of vegetables, fruit", "zh": "蔬菜水果制品"},
    "21": {"en": "Miscellaneous edible preparations", "zh": "杂项食品"},
    "22": {"en": "Beverages, spirits and vinegar", "zh": "饮料、酒及醋"},
    "25": {"en": "Salt; sulphur; earths and stone", "zh": "盐；硫磺；土石"},
    "27": {"en": "Mineral fuels, oils", "zh": "矿物燃料"},
    "28": {"en": "Inorganic chemicals", "zh": "无机化学品"},
    "29": {"en": "Organic chemicals", "zh": "有机化学品"},
    "30": {"en": "Pharmaceutical products", "zh": "药品"},
    "32": {"en": "Tanning or dyeing extracts", "zh": "鞣料；染料"},
    "33": {"en": "Essential oils; cosmetics", "zh": "精油；化妆品"},
    "34": {"en": "Soap; lubricants; waxes", "zh": "肥皂；蜡"},
    "35": {"en": "Albuminoidal substances; glues", "zh": "蛋白类物质；胶"},
    "38": {"en": "Miscellaneous chemical products", "zh": "杂项化学品"},
    "39": {"en": "Plastics and articles thereof", "zh": "塑料及其制品"},
    "40": {"en": "Rubber and articles thereof", "zh": "橡胶及其制品"},
    "42": {"en": "Leather articles; handbags", "zh": "皮革制品"},
    "44": {"en": "Wood and articles of wood", "zh": "木及木制品"},
    "48": {"en": "Paper and paperboard", "zh": "纸及纸板"},
    "49": {"en": "Printed books, newspapers", "zh": "书籍、报纸"},
    "50": {"en": "Silk", "zh": "丝"},
    "51": {"en": "Wool, fine animal hair", "zh": "羊毛"},
    "52": {"en": "Cotton", "zh": "棉花"},
    "54": {"en": "Man-made filaments", "zh": "化学纤维长丝"},
    "55": {"en": "Man-made staple fibres", "zh": "化学纤维短纤"},
    "56": {"en": "Wadding, felt and nonwovens", "zh": "絮胎；毡"},
    "60": {"en": "Knitted or crocheted fabrics", "zh": "针织物"},
    "61": {"en": "Knitted clothing", "zh": "针织服装"},
    "62": {"en": "Woven clothing", "zh": "非针织服装"},
    "63": {"en": "Other textile articles", "zh": "其他纺织制品"},
    "64": {"en": "Footwear", "zh": "鞋靴"},
    "65": {"en": "Headgear", "zh": "帽类"},
    "68": {"en": "Articles of stone, plaster, cement", "zh": "石料、水泥制品"},
    "69": {"en": "Ceramic products", "zh": "陶瓷产品"},
    "70": {"en": "Glass and glassware", "zh": "玻璃及制品"},
    "71": {"en": "Precious metals; jewellery", "zh": "贵金属；珠宝"},
    "72": {"en": "Iron and steel", "zh": "钢铁"},
    "73": {"en": "Articles of iron or steel", "zh": "钢铁制品"},
    "74": {"en": "Copper and articles thereof", "zh": "铜及其制品"},
    "76": {"en": "Aluminium and articles thereof", "zh": "铝及其制品"},
    "82": {"en": "Tools, cutlery of base metal", "zh": "贱金属工具刀具"},
    "83": {"en": "Miscellaneous articles of base metal", "zh": "贱金属杂项制品"},
    "84": {"en": "Nuclear reactors, boilers, machinery", "zh": "核反应堆；机械器具"},
    "85": {"en": "Electrical machinery and equipment", "zh": "电机、电气设备"},
    "86": {"en": "Railway or tramway locomotives", "zh": "铁道车辆"},
    "87": {"en": "Vehicles other than railway", "zh": "车辆及其零件"},
    "88": {"en": "Aircraft, spacecraft", "zh": "航空器、航天器"},
    "89": {"en": "Ships, boats", "zh": "船舶"},
    "90": {"en": "Optical, photographic, measuring instruments", "zh": "光学、计量仪器"},
    "91": {"en": "Clocks and watches", "zh": "钟表"},
    "92": {"en": "Musical instruments", "zh": "乐器"},
    "94": {"en": "Furniture; bedding; lighting", "zh": "家具；寝具；灯具"},
    "95": {"en": "Toys, games and sports", "zh": "玩具、游戏、运动用品"},
    "96": {"en": "Miscellaneous manufactured articles", "zh": "杂项制品"},
    "97": {"en": "Works of art, antiques", "zh": "艺术品、古董"},
}

# Common tariff reference (illustrative, not legally binding)
_REFERENCE_TARIFFS: dict[str, dict[str, float]] = {
    "US": {"default_rate": 3.5, "gsp_rate": 0.0, "mfn_rate": 3.5},
    "EU": {"default_rate": 4.0, "gsp_rate": 0.0, "mfn_rate": 4.0},
    "JP": {"default_rate": 3.0, "gsp_rate": 0.0, "mfn_rate": 3.0},
    "KR": {"default_rate": 8.0, "gsp_rate": 0.0, "mfn_rate": 8.0},
    "IN": {"default_rate": 10.0, "gsp_rate": 5.0, "mfn_rate": 10.0},
    "BR": {"default_rate": 14.0, "gsp_rate": 7.0, "mfn_rate": 14.0},
    "AU": {"default_rate": 5.0, "gsp_rate": 0.0, "mfn_rate": 5.0},
}

# Export-controlled categories (simplified)
_EXPORT_CONTROL_CHAPTERS = {
    "84": "Dual-use machinery (nuclear, chemical processing)",
    "85": "Electronics with potential military application",
    "88": "Aircraft and spacecraft components",
    "90": "Precision instruments (targeting, guidance)",
    "93": "Arms and ammunition (ITAR controlled)",
}


# ---------------------------------------------------------------------------
# HS Code operations
# ---------------------------------------------------------------------------

def lookup_hs_chapter(chapter_code: str) -> dict | None:
    """
    Look up HS chapter information by 2-digit code.

    Args:
        chapter_code: 2-digit HS chapter code (e.g., "85")

    Returns:
        Dict with code, en, zh descriptions, or None if not found
    """
    chapter_code = chapter_code.strip().zfill(2)[:2]
    info = HS_CHAPTERS.get(chapter_code)
    if info:
        return {"code": chapter_code, **info}
    return None


def validate_hs_code(hs_code: str) -> dict:
    """
    Validate and parse an HS code.

    Args:
        hs_code: HS code string (4-10 digits)

    Returns:
        Dict with:
          valid (bool), chapter, heading, subheading,
          chapter_info, formatted_code, digit_level
    """
    # Clean input
    cleaned = "".join(c for c in hs_code if c.isdigit())

    result = {
        "valid": False,
        "original": hs_code,
        "cleaned": cleaned,
        "chapter": "",
        "heading": "",
        "subheading": "",
        "chapter_info": None,
        "formatted_code": "",
        "digit_level": len(cleaned),
        "errors": [],
    }

    if len(cleaned) < 4:
        result["errors"].append("HS code must be at least 4 digits")
        return result

    if len(cleaned) > 10:
        result["errors"].append("HS code cannot exceed 10 digits")
        return result

    # Parse components
    result["chapter"] = cleaned[:2]
    result["heading"] = cleaned[:4]
    if len(cleaned) >= 6:
        result["subheading"] = cleaned[:6]

    # Validate chapter exists
    chapter_info = lookup_hs_chapter(cleaned[:2])
    if not chapter_info:
        result["errors"].append(f"Unknown HS chapter: {cleaned[:2]}")
        return result

    result["chapter_info"] = chapter_info
    result["valid"] = True

    # Format with dots
    if len(cleaned) >= 6:
        result["formatted_code"] = f"{cleaned[:4]}.{cleaned[4:6]}"
        if len(cleaned) > 6:
            result["formatted_code"] += f".{cleaned[6:]}"
    else:
        result["formatted_code"] = cleaned[:4]

    return result


def search_hs_chapters(query: str) -> list[dict]:
    """
    Search HS chapters by keyword (English or Chinese).

    Args:
        query: Search term

    Returns:
        List of matching chapter dicts
    """
    query_lower = query.lower()
    results = []
    for code, info in HS_CHAPTERS.items():
        if (query_lower in info["en"].lower() or
                query_lower in info["zh"] or
                query_lower in code):
            results.append({"code": code, **info})
    return results


# ---------------------------------------------------------------------------
# Tariff & duty calculations
# ---------------------------------------------------------------------------

def get_tariff_info(
    hs_code: str,
    destination_country: str,
    origin_country: str = "CN",
) -> dict:
    """
    Get tariff/duty rate information for a product.

    Args:
        hs_code: HS code (6+ digits)
        destination_country: 2-letter ISO country code of importer
        origin_country: 2-letter ISO country code of exporter (default: CN)

    Returns:
        Dict with duty_rate_pct, trade_agreement, additional_duties, notes
    """
    # Check cache first
    cache_key = f"tariff_{hs_code}_{destination_country}_{origin_country}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Try external API if configured
    api_key = get_secret("TRADE_DATA_API_KEY")
    if api_key:
        result = _fetch_tariff_api(hs_code, destination_country, origin_country, api_key)
        if result:
            _set_cached(cache_key, result)
            return result

    # Fall back to reference data
    country_upper = destination_country.upper()
    ref = _REFERENCE_TARIFFS.get(country_upper)

    if ref:
        result = {
            "hs_code": hs_code,
            "destination": destination_country,
            "origin": origin_country,
            "mfn_rate_pct": ref["mfn_rate"],
            "applied_rate_pct": ref["default_rate"],
            "gsp_rate_pct": ref["gsp_rate"],
            "trade_agreements": _get_trade_agreements(origin_country, destination_country),
            "additional_duties": _get_additional_duties(hs_code, destination_country),
            "notes": "Reference data — verify with customs authority before quoting",
            "source": "reference",
            "last_updated": "2024-01",
        }
    else:
        result = {
            "hs_code": hs_code,
            "destination": destination_country,
            "origin": origin_country,
            "mfn_rate_pct": None,
            "applied_rate_pct": None,
            "notes": f"No tariff data available for {destination_country}. Please check local customs.",
            "source": "none",
        }

    _set_cached(cache_key, result)
    return result


def calculate_duty(
    hs_code: str,
    cif_value_usd: float,
    destination_country: str,
    origin_country: str = "CN",
    quantity: int = 1,
) -> dict:
    """
    Calculate estimated import duty for a shipment.

    Args:
        hs_code: HS code for the product
        cif_value_usd: CIF value in USD
        destination_country: Importing country
        origin_country: Exporting country
        quantity: Number of units (for specific duties)

    Returns:
        Dict with duty_amount_usd, vat_amount_usd, total_landed_cost, breakdown
    """
    tariff = get_tariff_info(hs_code, destination_country, origin_country)
    rate = tariff.get("applied_rate_pct")

    if rate is None:
        return {
            "success": False,
            "message": "Cannot calculate — no tariff rate available",
            "hs_code": hs_code,
        }

    duty_amount = cif_value_usd * (rate / 100)

    # Estimate VAT (common rates by country)
    vat_rates = {
        "US": 0.0, "EU": 20.0, "UK": 20.0, "JP": 10.0, "KR": 10.0,
        "AU": 10.0, "CA": 5.0, "IN": 18.0, "BR": 17.0, "MX": 16.0,
    }
    vat_rate = vat_rates.get(destination_country.upper(), 15.0)
    vat_base = cif_value_usd + duty_amount
    vat_amount = vat_base * (vat_rate / 100)

    total_landed = cif_value_usd + duty_amount + vat_amount

    return {
        "success": True,
        "hs_code": hs_code,
        "cif_value_usd": cif_value_usd,
        "duty_rate_pct": rate,
        "duty_amount_usd": round(duty_amount, 2),
        "vat_rate_pct": vat_rate,
        "vat_amount_usd": round(vat_amount, 2),
        "total_landed_cost_usd": round(total_landed, 2),
        "per_unit_landed_cost": round(total_landed / max(quantity, 1), 2),
        "breakdown": {
            "CIF Value": f"${cif_value_usd:,.2f}",
            f"Import Duty ({rate}%)": f"${duty_amount:,.2f}",
            f"VAT/GST ({vat_rate}%)": f"${vat_amount:,.2f}",
            "Total Landed Cost": f"${total_landed:,.2f}",
        },
        "destination": destination_country,
        "origin": origin_country,
        "disclaimer": "Estimates only. Actual duties may vary. Consult customs broker.",
    }


# ---------------------------------------------------------------------------
# Trade statistics
# ---------------------------------------------------------------------------

def get_trade_stats(
    hs_code: str,
    country: str = "",
    year: int = 0,
) -> dict:
    """
    Get trade statistics for a product/country.

    Args:
        hs_code: HS code (2-6 digits)
        country: Country code to focus on (empty = global)
        year: Year for statistics (0 = latest available)

    Returns:
        Dict with import/export values, top trading partners, trends
    """
    # Try external API
    api_key = get_secret("TRADE_DATA_API_KEY")
    if api_key:
        result = _fetch_trade_stats_api(hs_code, country, year, api_key)
        if result:
            return result

    # Return reference guidance
    chapter = hs_code[:2] if len(hs_code) >= 2 else ""
    chapter_info = HS_CHAPTERS.get(chapter, {})

    return {
        "hs_code": hs_code,
        "chapter": chapter,
        "chapter_description": chapter_info.get("en", "Unknown"),
        "data_available": False,
        "suggestion": (
            "For detailed trade statistics, configure TRADE_DATA_API_KEY "
            "with a UN Comtrade or TradeMap API key. "
            "Alternatively, visit: https://comtrade.un.org/data/ for free lookup."
        ),
        "free_resources": [
            {"name": "UN Comtrade", "url": "https://comtrade.un.org/data/"},
            {"name": "ITC Trade Map", "url": "https://www.trademap.org/"},
            {"name": "WTO Statistics", "url": "https://stats.wto.org/"},
        ],
    }


# ---------------------------------------------------------------------------
# Export controls
# ---------------------------------------------------------------------------

def check_export_controls(
    hs_code: str,
    destination_country: str,
    origin_country: str = "CN",
) -> dict:
    """
    Check if a product may be subject to export controls.

    This is a HIGH-LEVEL advisory check. Users must consult legal counsel
    for actual export compliance.

    Args:
        hs_code: Product HS code
        destination_country: Where the product is being shipped
        origin_country: Where it's shipping from

    Returns:
        Dict with risk_level (low/medium/high), alerts, recommendations
    """
    chapter = hs_code[:2] if len(hs_code) >= 2 else ""
    alerts = []
    risk_level = "low"

    # Check if chapter is in controlled categories
    if chapter in _EXPORT_CONTROL_CHAPTERS:
        alerts.append({
            "type": "category_control",
            "message": f"HS Chapter {chapter} may include controlled items: "
                       f"{_EXPORT_CONTROL_CHAPTERS[chapter]}",
            "severity": "high",
        })
        risk_level = "high"

    # Check sanctioned destinations (simplified list)
    sanctioned_countries = {"KP", "IR", "SY", "CU", "VE"}
    if destination_country.upper() in sanctioned_countries:
        alerts.append({
            "type": "sanctioned_destination",
            "message": f"Destination {destination_country} is subject to comprehensive sanctions. "
                       "Export may be prohibited.",
            "severity": "critical",
        })
        risk_level = "critical"

    # Dual-use technology checks
    dual_use_headings = {"8401", "8464", "8543", "8548", "9013", "9014", "9015"}
    heading = hs_code[:4] if len(hs_code) >= 4 else ""
    if heading in dual_use_headings:
        alerts.append({
            "type": "dual_use",
            "message": f"HS heading {heading} may include dual-use items "
                       "requiring export license.",
            "severity": "medium",
        })
        if risk_level == "low":
            risk_level = "medium"

    recommendations = []
    if risk_level in ("high", "critical"):
        recommendations = [
            "Consult a licensed customs broker or trade compliance attorney",
            "Check EAR (Export Administration Regulations) classification",
            "Verify end-user and end-use declarations",
            "Apply for export license if required",
        ]
    elif risk_level == "medium":
        recommendations = [
            "Verify the specific product against control lists",
            "Maintain end-user documentation",
            "Consider consulting a trade compliance specialist",
        ]

    return {
        "hs_code": hs_code,
        "destination": destination_country,
        "origin": origin_country,
        "risk_level": risk_level,
        "alerts": alerts,
        "recommendations": recommendations,
        "disclaimer": (
            "This is an automated advisory check only. It does NOT constitute "
            "legal advice. Always verify with qualified trade compliance counsel."
        ),
    }


# ---------------------------------------------------------------------------
# Import requirements
# ---------------------------------------------------------------------------

def get_import_requirements(
    hs_code: str,
    destination_country: str,
) -> dict:
    """
    Get import documentation and certification requirements.

    Args:
        hs_code: Product HS code
        destination_country: Importing country

    Returns:
        Dict with required_documents, certifications, notes
    """
    chapter = hs_code[:2] if len(hs_code) >= 2 else ""

    # Common documents required for most shipments
    base_documents = [
        "Commercial Invoice",
        "Packing List",
        "Bill of Lading / Air Waybill",
        "Certificate of Origin",
    ]

    # Chapter-specific requirements
    additional_docs = []
    certifications = []

    if chapter in ("01", "02", "03", "04", "05"):
        additional_docs.extend(["Phytosanitary Certificate", "Health Certificate"])
        certifications.append("USDA/EU Food Safety approval")
    elif chapter in ("28", "29", "38"):
        additional_docs.append("Material Safety Data Sheet (MSDS)")
        certifications.append("REACH compliance (EU)")
    elif chapter == "30":
        additional_docs.extend(["Drug Registration Certificate", "GMP Certificate"])
        certifications.append("FDA/EMA registration")
    elif chapter in ("84", "85"):
        certifications.extend(["CE Marking (EU)", "FCC (US)", "CCC (China)"])
    elif chapter == "87":
        additional_docs.append("Vehicle Type Approval")
        certifications.append("ECE/DOT compliance")
    elif chapter in ("61", "62", "63"):
        certifications.extend(["OEKO-TEX (textile safety)", "CPSIA (US children's)"])
    elif chapter == "94":
        certifications.extend(["CARB (US furniture)", "EN standards (EU)"])
    elif chapter == "95":
        certifications.extend(["ASTM F963 (US toys)", "EN 71 (EU toys)", "CPC certificate"])

    # Country-specific requirements
    country_notes = {
        "US": "FDA prior notice required for food. CPSC compliance for consumer products.",
        "EU": "CE marking mandatory for most industrial/consumer goods. REACH for chemicals.",
        "JP": "PSE mark for electrical. JIS standards. Food Sanitation Act for food.",
        "KR": "KC mark for electronics. KFDA for food/cosmetics.",
        "AU": "ACCC product safety standards. Quarantine inspection for organic goods.",
        "IN": "BIS certification for many products. Import license for restricted items.",
        "BR": "INMETRO certification. ANVISA for health products.",
    }

    return {
        "hs_code": hs_code,
        "destination": destination_country,
        "required_documents": base_documents + additional_docs,
        "certifications": certifications,
        "country_notes": country_notes.get(destination_country.upper(), ""),
        "general_advice": [
            "Verify all requirements with destination country customs authority",
            "Documents should be in English + local language when required",
            "Keep copies of all documents for minimum 5 years",
            "Consider hiring a licensed customs broker for complex shipments",
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_trade_agreements(origin: str, destination: str) -> list[str]:
    """Get applicable trade agreements between two countries."""
    agreements = []
    pair = frozenset([origin.upper(), destination.upper()])

    fta_database = {
        frozenset(["CN", "AU"]): "ChAFTA (China-Australia FTA)",
        frozenset(["CN", "KR"]): "China-Korea FTA",
        frozenset(["CN", "JP"]): "RCEP",
        frozenset(["CN", "NZ"]): "China-New Zealand FTA",
        frozenset(["CN", "SG"]): "China-Singapore FTA / RCEP",
        frozenset(["CN", "TH"]): "ASEAN-China FTA / RCEP",
        frozenset(["CN", "MY"]): "ASEAN-China FTA / RCEP",
    }

    for fta_pair, name in fta_database.items():
        if pair == fta_pair:
            agreements.append(name)

    # RCEP members
    rcep_members = {"CN", "JP", "KR", "AU", "NZ", "SG", "TH", "MY", "ID", "PH", "VN", "BN", "KH", "LA", "MM"}
    if origin.upper() in rcep_members and destination.upper() in rcep_members:
        if "RCEP" not in " ".join(agreements):
            agreements.append("RCEP")

    return agreements


def _get_additional_duties(hs_code: str, country: str) -> list[dict]:
    """Get any additional duties (anti-dumping, countervailing, etc.)."""
    # Simplified: return empty for now
    # In production, would check against anti-dumping duty databases
    return []


def _get_cached(key: str) -> dict | None:
    """Get a value from the customs data cache."""
    cache = load_json(_CACHE_FILE, default={})
    if not isinstance(cache, dict):
        return None
    entry = cache.get(key)
    if not entry:
        return None
    # Check TTL
    cached_at = entry.get("_cached_at", "")
    if cached_at:
        try:
            cached_time = datetime.fromisoformat(cached_at)
            from datetime import timedelta
            if datetime.now() - cached_time > timedelta(hours=_CACHE_TTL_HOURS):
                return None  # Expired
        except (ValueError, TypeError):
            pass
    return entry.get("data")


def _set_cached(key: str, data: dict) -> None:
    """Set a value in the customs data cache."""
    cache = load_json(_CACHE_FILE, default={})
    if not isinstance(cache, dict):
        cache = {}
    cache[key] = {
        "data": data,
        "_cached_at": datetime.now().isoformat(),
    }
    # Cap cache size
    if len(cache) > 500:
        # Remove oldest entries
        sorted_keys = sorted(
            cache.keys(),
            key=lambda k: cache[k].get("_cached_at", ""),
        )
        for old_key in sorted_keys[:100]:
            del cache[old_key]
    save_json(_CACHE_FILE, cache)


def _fetch_tariff_api(
    hs_code: str, destination: str, origin: str, api_key: str
) -> dict | None:
    """Fetch tariff data from external API."""
    # Placeholder for external API integration
    # Would connect to TradeMap, WITS, or similar service
    logger.debug("External tariff API not yet integrated (hs=%s, dest=%s)", hs_code, destination)
    return None


def _fetch_trade_stats_api(
    hs_code: str, country: str, year: int, api_key: str
) -> dict | None:
    """Fetch trade statistics from external API."""
    logger.debug("External trade stats API not yet integrated (hs=%s)", hs_code)
    return None
