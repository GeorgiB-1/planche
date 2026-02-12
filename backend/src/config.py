"""
Central configuration module for the Planche.bg backend.

Loads environment variables, defines constants, budget tiers,
room allocations, furniture requirements, target scraping sites,
and LLM prompt templates.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "planche-images")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))

# ---------------------------------------------------------------------------
# Currency conversion
# ---------------------------------------------------------------------------
BGN_TO_EUR_RATE = 1.9558  # Fixed BGN/EUR exchange rate

# ---------------------------------------------------------------------------
# Bulgarian -> English category & subcategory mapping
# ---------------------------------------------------------------------------
BG_TO_EN_CATEGORY: dict[str, str] = {
    # Main categories
    "Дивани": "sofa",
    "Маси": "table",
    "Столове": "chair",
    "Легла": "bed",
    "Гардероби": "wardrobe",
    "Шкафове": "cabinet",
    "Бюра": "desk",
    "Рафтове": "shelf",
    "Осветление": "lamp",
    "Килими": "rug",
    "Огледала": "mirror",
    "Матраци": "mattress",
    # Subcategories
    "ъглов диван": "corner sofa",
    "диван-легло": "sofa bed",
    "маса за хранене": "dining table",
    "журнална маса": "coffee table",
    "трапезарен стол": "dining chair",
    "офис стол": "office chair",
    "двойно легло": "double bed",
    "единично легло": "single bed",
    "скрин": "dresser",
    "нощно шкафче": "nightstand",
    "етажерка": "shelf unit",
    "библиотека": "bookcase",
    "настолна лампа": "table lamp",
    "подова лампа": "floor lamp",
}

# ---------------------------------------------------------------------------
# Budget tiers
# ---------------------------------------------------------------------------
BUDGET_TIERS: dict[str, dict] = {
    "budget": {
        "label": "Бюджетен / Budget",
        "description": (
            "Cost-effective furnishing focused on functionality and value. "
            "Leverages flat-pack and mass-market retailers for the best "
            "price-to-quality ratio."
        ),
        "per_sqm_eur": (40, 80),
        "preferred_sources": ["ikea.bg", "jysk.bg", "emag.bg"],
        "max_single_item_pct": 0.30,
        "style_keywords": [
            "minimalist", "scandinavian", "modern", "functional", "simple",
        ],
    },
    "standard": {
        "label": "Стандартен / Standard",
        "description": (
            "Balanced approach combining quality essentials with select "
            "statement pieces. A mix of mid-range and value retailers."
        ),
        "per_sqm_eur": (80, 150),
        "preferred_sources": ["ikea.bg", "aiko-bg.com", "videnov.bg", "jysk.bg"],
        "max_single_item_pct": 0.25,
        "style_keywords": [
            "contemporary", "transitional", "mid-century", "scandinavian",
            "modern",
        ],
    },
    "premium": {
        "label": "Премиум / Premium",
        "description": (
            "High-quality furnishing with attention to materials, design "
            "and durability. Emphasis on curated aesthetics."
        ),
        "per_sqm_eur": (150, 300),
        "preferred_sources": ["aiko-bg.com", "videnov.bg", "ikea.bg"],
        "max_single_item_pct": 0.20,
        "style_keywords": [
            "contemporary", "mid-century modern", "industrial chic",
            "art deco", "japandi",
        ],
    },
    "luxury": {
        "label": "Лукс / Luxury",
        "description": (
            "Top-tier furnishing with designer pieces, premium materials "
            "and bespoke options. No compromises on quality or style."
        ),
        "per_sqm_eur": (300, 600),
        "preferred_sources": ["aiko-bg.com", "videnov.bg"],
        "max_single_item_pct": 0.15,
        "style_keywords": [
            "luxury modern", "designer", "bespoke", "art deco",
            "contemporary classic", "high-end minimalist",
        ],
    },
}

# ---------------------------------------------------------------------------
# Room budget allocation  (percentage ranges per furniture category)
# ---------------------------------------------------------------------------
ROOM_BUDGET_ALLOCATION: dict[str, dict[str, tuple[float, float]]] = {
    "living_room": {
        "seating": (0.30, 0.40),
        "tables": (0.10, 0.15),
        "storage": (0.10, 0.15),
        "lighting": (0.05, 0.10),
        "rugs": (0.05, 0.10),
        "decor": (0.05, 0.10),
    },
    "bedroom": {
        "bed": (0.35, 0.45),
        "mattress": (0.20, 0.30),
        "storage": (0.10, 0.20),
        "nightstands": (0.05, 0.10),
        "lighting": (0.05, 0.10),
        "decor": (0.03, 0.07),
    },
    "kitchen": {
        "dining_table": (0.25, 0.35),
        "dining_chairs": (0.20, 0.30),
        "storage": (0.15, 0.25),
        "lighting": (0.05, 0.10),
        "accessories": (0.05, 0.10),
    },
    "dining_room": {
        "dining_table": (0.30, 0.40),
        "dining_chairs": (0.25, 0.35),
        "storage": (0.10, 0.20),
        "lighting": (0.05, 0.10),
        "decor": (0.05, 0.10),
    },
    "office": {
        "desk": (0.30, 0.40),
        "chair": (0.25, 0.35),
        "storage": (0.10, 0.20),
        "shelving": (0.05, 0.15),
        "lighting": (0.05, 0.10),
        "accessories": (0.03, 0.07),
    },
    "kids_room": {
        "bed": (0.25, 0.35),
        "mattress": (0.15, 0.20),
        "desk": (0.10, 0.20),
        "storage": (0.15, 0.25),
        "lighting": (0.05, 0.10),
        "decor": (0.05, 0.10),
    },
}

# ---------------------------------------------------------------------------
# Room furniture requirements  (required & optional slots per room type)
# ---------------------------------------------------------------------------
ROOM_FURNITURE_REQUIREMENTS: dict[str, dict[str, list]] = {
    "living_room": {
        "required": [
            {"slot": "main_seating", "categories": ["sofa", "corner sofa", "sofa bed"], "quantity": 1},
            {"slot": "coffee_table", "categories": ["coffee table", "table"], "quantity": 1},
            {"slot": "main_lighting", "categories": ["lamp", "floor lamp"], "quantity": 1},
        ],
        "optional": [
            {"slot": "accent_chair", "categories": ["chair"], "quantity": 1},
            {"slot": "tv_stand", "categories": ["cabinet"], "quantity": 1},
            {"slot": "bookcase", "categories": ["bookcase", "shelf", "shelf unit"], "quantity": 1},
            {"slot": "rug", "categories": ["rug"], "quantity": 1},
            {"slot": "side_table", "categories": ["table", "coffee table"], "quantity": 1},
            {"slot": "accent_lighting", "categories": ["table lamp", "lamp"], "quantity": 1},
            {"slot": "mirror", "categories": ["mirror"], "quantity": 1},
        ],
    },
    "bedroom": {
        "required": [
            {"slot": "bed", "categories": ["bed", "double bed", "single bed"], "quantity": 1},
            {"slot": "mattress", "categories": ["mattress"], "quantity": 1},
            {"slot": "wardrobe", "categories": ["wardrobe"], "quantity": 1},
        ],
        "optional": [
            {"slot": "nightstand", "categories": ["nightstand"], "quantity": 2},
            {"slot": "dresser", "categories": ["dresser", "cabinet"], "quantity": 1},
            {"slot": "bedside_lamp", "categories": ["table lamp", "lamp"], "quantity": 2},
            {"slot": "mirror", "categories": ["mirror"], "quantity": 1},
            {"slot": "rug", "categories": ["rug"], "quantity": 1},
            {"slot": "accent_chair", "categories": ["chair"], "quantity": 1},
        ],
    },
    "kitchen": {
        "required": [
            {"slot": "dining_table", "categories": ["dining table", "table"], "quantity": 1},
            {"slot": "dining_chairs", "categories": ["dining chair", "chair"], "quantity": 4},
        ],
        "optional": [
            {"slot": "storage_cabinet", "categories": ["cabinet"], "quantity": 1},
            {"slot": "shelf_unit", "categories": ["shelf", "shelf unit"], "quantity": 1},
            {"slot": "pendant_light", "categories": ["lamp"], "quantity": 1},
        ],
    },
    "office": {
        "required": [
            {"slot": "desk", "categories": ["desk"], "quantity": 1},
            {"slot": "office_chair", "categories": ["office chair", "chair"], "quantity": 1},
        ],
        "optional": [
            {"slot": "bookcase", "categories": ["bookcase", "shelf", "shelf unit"], "quantity": 1},
            {"slot": "filing_cabinet", "categories": ["cabinet"], "quantity": 1},
            {"slot": "desk_lamp", "categories": ["table lamp", "lamp"], "quantity": 1},
            {"slot": "rug", "categories": ["rug"], "quantity": 1},
        ],
    },
}

# ---------------------------------------------------------------------------
# Target scraping sites
# ---------------------------------------------------------------------------
TARGET_SITES: list[dict] = [
    {
        "name": "Belcaro",
        "domain": "belcaro.bg",
        "url": "https://belcaro.bg/catalog",
        "priority": "HIGH",
        "wait_for": 3000,
        "only_main_content": True,
        "use_proxy": False,
    },
]

# ---------------------------------------------------------------------------
# LLM Prompts
# ---------------------------------------------------------------------------

PRODUCT_EXTRACTION_PROMPT = """\
You are a structured data extraction engine for a Bulgarian furniture e-commerce \
aggregator. You will receive raw Markdown scraped from a Bulgarian furniture \
retailer's product page.

Your task is to extract ALL product information into a strict JSON format.

## Extraction rules

1. **name** -- Keep the original Bulgarian product name exactly as-is. Do NOT \
translate it.
2. **brand** -- Extract the brand/manufacturer if mentioned; otherwise null.
3. **sku** -- Extract any SKU, article number or product code; otherwise null.
4. **price** -- Extract the numeric price. Include the currency as a separate \
field ("BGN" or "EUR"). If a discounted price is present, use the discounted \
price as `price` and put the original in `original_price`.
5. **currency** -- "BGN" or "EUR".
6. **original_price** -- The non-discounted price if a sale is active; otherwise null.
7. **dimensions** -- An object with `width_cm`, `height_cm`, `depth_cm` as \
numbers. Parse from any format (e.g. "Ш120 x В75 x Д60 см", "120/75/60", \
etc.). Use null for any dimension not found.
8. **materials** -- A list of materials mentioned (e.g. ["дърво", "метал", \
"текстил"]). Keep original Bulgarian terms.
9. **colors** -- A list of colors mentioned. Keep original Bulgarian terms.
10. **category** -- Map to one of the standard categories: sofa, table, chair, \
bed, wardrobe, cabinet, desk, shelf, lamp, rug, mirror, mattress. Use English.
11. **subcategory** -- A more specific English subcategory if determinable \
(e.g. "corner sofa", "dining table", "office chair"). Otherwise null.
12. **room_type** -- Likely room(s) this product belongs in: living_room, \
bedroom, kitchen, dining_room, office, kids_room, bathroom, hallway. Can be a list.
13. **style** -- Classify the style: modern, scandinavian, industrial, classic, \
minimalist, mid-century, art_deco, rustic, contemporary, traditional. Use English.
14. **description** -- A concise English-language summary of the product \
(1-2 sentences).
15. **description_bg** -- The original Bulgarian product description from the page, \
copied verbatim. If no description is found on the page, return null.
16. **features** -- A list of notable features in English \
(e.g. ["convertible", "storage compartment", "adjustable height"]).
17. **in_stock** -- Boolean. True if the product appears to be available.
18. **delivery_info** -- Any delivery/shipping information found; otherwise null.
19. **rating** -- Numeric rating if present (e.g. 4.5); otherwise null.
20. **image_urls** -- A list of all product image URLs found.

## Output format

Return ONLY a valid JSON object (no markdown fencing, no extra text) with the \
fields above. If the page contains multiple products, return a JSON array of \
objects. If no product data can be extracted, return: {{"error": "no_product_data"}}.

## Scraped Markdown

{markdown}
"""

PRODUCT_VISION_PROMPT = """\
You are a furniture analysis AI for an interior design platform. You will \
receive one or more images of a furniture product. Analyze each image and \
return a single consolidated JSON object with the following fields:

1. **dimensions_estimate** -- If no exact dimensions are provided, estimate \
approximate dimensions in cm based on visual cues and typical furniture \
proportions:
   - `width_cm` (number or null)
   - `height_cm` (number or null)
   - `depth_cm` (number or null)
   - `confidence` ("high", "medium", "low")

2. **proportion_ratios** -- Estimated proportions useful for 3D placement:
   - `width_to_height` (float)
   - `width_to_depth` (float)
   - `seat_height_ratio` (float or null, for seating furniture only)

3. **visual_description** -- A detailed English description of the product's \
visual appearance suitable for use in rendering prompts. Include shape, form \
factor, silhouette, and notable design elements. 2-3 sentences.

4. **material_analysis** -- List of detected materials with confidence:
   - Each entry: {"material": "...", "location": "...", "confidence": "high|medium|low"}
   - e.g. {"material": "oak veneer", "location": "tabletop", "confidence": "high"}

5. **color_analysis** -- Detailed color breakdown:
   - `primary_color`: {"name": "...", "hex_estimate": "#..."}
   - `secondary_colors`: [{"name": "...", "hex_estimate": "#...", "location": "..."}]
   - `overall_tone`: "warm" | "cool" | "neutral"

6. **style_classification** -- Classify into one or more styles with confidence:
   - Each entry: {"style": "...", "confidence": "high|medium|low"}
   - Possible styles: modern, scandinavian, industrial, classic, minimalist, \
mid-century, art_deco, rustic, contemporary, traditional, bohemian, japandi.

7. **category_verification** -- Verify or suggest the product category:
   - `suggested_category`: English category name
   - `suggested_subcategory`: English subcategory or null
   - `confidence`: "high" | "medium" | "low"

8. **image_quality** -- Assess each image:
   - `overall_quality`: "high" | "medium" | "low"
   - `background`: "studio" | "room_scene" | "cutout" | "lifestyle"
   - `suitable_for_rendering`: boolean
   - `issues`: list of any problems (e.g. ["blurry", "watermarked", "low_resolution"])

Return ONLY a valid JSON object with the fields above. No markdown fencing, \
no extra commentary.
"""

ROOM_ANALYSIS_PROMPT = """\
You are a floor plan analysis AI for a Bulgarian interior design platform. \
You will receive an image of a floor plan sketch or architectural drawing. \
The sketch may contain labels in Bulgarian.

Analyze the floor plan and extract structured room data as JSON.

## Extraction rules

1. **rooms** -- A list of detected rooms. For each room provide:
   - `name`: Room name in English (e.g. "living_room", "bedroom", "kitchen")
   - `name_bg`: Original Bulgarian label if present (e.g. "Хол", "Спалня")
   - `dimensions`: {"length_m": float, "width_m": float, "area_sqm": float}
   - `shape`: "rectangular" | "L-shaped" | "irregular" | "other"

2. **windows** -- For each room, list detected windows:
   - `wall`: "north" | "south" | "east" | "west" (or approximate)
   - `width_m`: estimated width
   - `position`: description of position along the wall

3. **doors** -- For each room, list detected doors:
   - `wall`: wall location
   - `type`: "interior" | "exterior" | "balcony"
   - `width_m`: estimated width
   - `connects_to`: adjacent room name or "exterior"

4. **usable_walls** -- For each room, list walls available for furniture:
   - `wall`: wall identifier
   - `length_m`: usable length (excluding doors/windows)
   - `obstructions`: list of items blocking the wall (radiator, door swing, etc.)

5. **furniture_zones** -- For each room, suggest logical furniture placement zones:
   - `zone_name`: e.g. "seating_area", "sleeping_area", "work_area", "dining_area"
   - `position`: description relative to room features
   - `dimensions`: {"length_m": float, "width_m": float}
   - `suitable_for`: list of furniture categories that fit

6. **overall_layout** -- High-level observations:
   - `total_area_sqm`: estimated total area
   - `layout_type`: "open_plan" | "traditional" | "studio" | "loft"
   - `natural_light`: "abundant" | "moderate" | "limited"
   - `flow_notes`: brief notes on room connectivity and traffic flow

## Bulgarian label mapping

Common Bulgarian room labels to handle:
- Хол / Дневна = living_room
- Спалня = bedroom
- Кухня = kitchen
- Баня / WC / Тоалетна = bathroom
- Коридор / Антре = hallway
- Балкон / Тераса = balcony
- Детска стая = kids_room
- Кабинет = office
- Трапезария = dining_room
- Мокро помещение = utility_room

Return ONLY a valid JSON object. No markdown fencing, no extra commentary.
"""

SCENE_DESCRIPTION_PROMPT = """\
You are an expert cinematographer and spatial analyst. You will receive an \
image of an interior design sketch, floor plan, or room photograph.

Your task is to analyze the CAMERA VIEWPOINT and SPATIAL COMPOSITION of the \
scene, NOT the architectural layout. Extract exhaustive data about how the \
scene is framed, what the camera sees, and how objects are arranged in the \
frame.

## Extraction rules

1. **camera** — Camera/viewpoint information:
   - `perspective_type`: "one-point" | "two-point" | "three-point" | \
"orthographic" | "birds-eye" | "worms-eye" | "isometric"
   - `eye_level`: "floor" | "seated" | "standing" | "elevated" | "overhead"
   - `eye_height_estimate`: string estimate (e.g. "~160 cm", "~300 cm")
   - `camera_position`: natural language description of where the camera is \
(e.g. "room entrance, slightly left of center", "corner of the room")
   - `camera_direction`: natural language description of where the camera \
looks (e.g. "looking toward the far wall", "looking diagonally across the room")
   - `horizontal_angle_deg`: 0-360 estimate, 0 = facing the primary/far wall
   - `vertical_tilt_deg`: negative = looking down, 0 = level, positive = up
   - `fov_estimate`: "narrow (~30°)" | "normal (~60°)" | "wide (~90°)" | \
"ultra-wide (~120°)"
   - `distance_to_subject`: "close" | "medium" | "far"

2. **visible_surfaces** — Which architectural surfaces are visible:
   - `floor_visible`: boolean
   - `floor_coverage_pct`: 0-100
   - `ceiling_visible`: boolean
   - `ceiling_coverage_pct`: 0-100
   - `walls`: list of objects, each with:
     - `wall_id`: identifier (e.g. "left_wall", "far_wall", "right_wall")
     - `coverage_pct`: 0-100 (how much of the frame this wall occupies)
     - `features`: list of notable features on this wall (e.g. "window", \
"door", "built-in shelving")

3. **objects** — Every distinct object or element visible in the sketch:
   - `name`: descriptive name (e.g. "sofa", "coffee_table", "floor_lamp")
   - `depth_zone`: "foreground" | "midground" | "background"
   - `horizontal_position`: "far-left" | "center-left" | "center" | \
"center-right" | "far-right"
   - `vertical_position`: "top" | "upper-middle" | "middle" | \
"lower-middle" | "bottom"
   - `size_in_frame`: "tiny" | "small" | "medium" | "large" | "dominant"
   - `occluded_by`: name of occluding object or null

4. **spatial_relationships** — All meaningful pairs:
   - `object_a`: name
   - `object_b`: name
   - `relationship`: "in_front_of" | "behind" | "to_left_of" | \
"to_right_of" | "above" | "below" | "on_top_of" | "next_to" | "inside"

5. **composition** — Visual composition analysis:
   - `dominant_lines`: list of line descriptions (e.g. "strong diagonal \
from bottom-left to upper-right", "horizontal ceiling line")
   - `focal_point`: what draws the eye first
   - `visual_weight`: "left-heavy" | "right-heavy" | "top-heavy" | \
"bottom-heavy" | "balanced"
   - `depth_cues`: list (e.g. "converging lines", "size diminution", \
"overlapping objects", "atmospheric perspective")
   - `balance`: "symmetric" | "asymmetric" | "radial"

6. **natural_language_summary** — Write a 5-10 sentence cinematographic \
description of the scene as if directing a camera operator. Describe the \
exact viewpoint, what is visible, the depth layers, and the overall \
composition. Be very specific about angles and positions.

7. **generation_directive** — Write a 2-4 sentence IMPERATIVE instruction \
that an image generation model MUST follow to reproduce this exact camera \
angle and composition. Start with "Render from..." and be extremely specific \
about eye level, camera position, direction, perspective type, and what \
should be visible in the frame.

Return ONLY a valid JSON object with the fields above. No markdown fencing, \
no extra commentary.
"""
