# Zone definitions for each store
# Coordinates are normalized (0-1) relative to frame width/height
# We'll refine these after seeing actual video frames

STORE_ZONES = {
    "store1": {
        "store_code": "ST1008",
        "cameras": {
            "CAM1": {
                "type": "zone",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1008_Z01",
                        "zone_name": "Left Shelf",
                        "zone_type": "SHELF",
                        "is_revenue_zone": True,
                        # x1, y1, x2, y2 normalized 0-1
                        "bbox": [0.0, 0.1, 0.45, 0.9]
                    },
                    {
                        "zone_id": "PURPLLE_ST1008_Z02",
                        "zone_name": "Right Shelf",
                        "zone_type": "SHELF",
                        "is_revenue_zone": True,
                        "bbox": [0.55, 0.1, 1.0, 0.9]
                    }
                ]
            },
            "CAM2": {
                "type": "zone",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1008_Z03",
                        "zone_name": "Center Display",
                        "zone_type": "DISPLAY",
                        "is_revenue_zone": True,
                        "bbox": [0.2, 0.1, 0.8, 0.9]
                    }
                ]
            },
            "CAM3": {
                "type": "entry",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1008_ENTRY",
                        "zone_name": "Store Entry",
                        "zone_type": "ENTRY",
                        "is_revenue_zone": False,
                        "bbox": [0.1, 0.0, 0.9, 0.4]
                    }
                ]
            },
            "CAM5": {
                "type": "billing",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1008_Z_BILLING_01",
                        "zone_name": "Billing Counter Queue",
                        "zone_type": "BILLING",
                        "is_revenue_zone": True,
                        "bbox": [0.0, 0.0, 1.0, 1.0]
                    }
                ]
            }
        }
    },
    "store2": {
        "store_code": "ST1076",
        "cameras": {
            "CAM1": {
                "type": "entry",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1076_ENTRY_01",
                        "zone_name": "Main Entry",
                        "zone_type": "ENTRY",
                        "is_revenue_zone": False,
                        "bbox": [0.1, 0.0, 0.9, 0.4]
                    }
                ]
            },
            "CAM2": {
                "type": "entry",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1076_ENTRY_02",
                        "zone_name": "Side Entry",
                        "zone_type": "ENTRY",
                        "is_revenue_zone": False,
                        "bbox": [0.1, 0.0, 0.9, 0.4]
                    }
                ]
            },
            "CAM3": {
                "type": "zone",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1076_Z01",
                        "zone_name": "Left Shelf",
                        "zone_type": "SHELF",
                        "is_revenue_zone": True,
                        "bbox": [0.0, 0.1, 0.45, 0.9]
                    },
                    {
                        "zone_id": "PURPLLE_ST1076_Z02",
                        "zone_name": "Lipstick Aisle",
                        "zone_type": "SHELF",
                        "is_revenue_zone": True,
                        "bbox": [0.55, 0.1, 1.0, 0.9]
                    }
                ]
            },
            "CAM4": {
                "type": "billing",
                "zones": [
                    {
                        "zone_id": "PURPLLE_ST1076_Z_BILLING_01",
                        "zone_name": "Billing Counter Queue",
                        "zone_type": "BILLING",
                        "is_revenue_zone": True,
                        "bbox": [0.0, 0.0, 1.0, 1.0]
                    }
                ]
            }
        }
    }
}

def get_zone_for_point(x_norm, y_norm, camera_config):
    """Given a normalized point, return which zone it falls in"""
    for zone in camera_config.get("zones", []):
        x1, y1, x2, y2 = zone["bbox"]
        if x1 <= x_norm <= x2 and y1 <= y_norm <= y2:
            return zone
    return None

def get_age_bucket(age):
    """Convert age to bucket string"""
    if age < 18:
        return "under-18"
    elif age <= 24:
        return "18-24"
    elif age <= 34:
        return "25-34"
    elif age <= 44:
        return "35-44"
    elif age <= 54:
        return "45-54"
    else:
        return "55+"