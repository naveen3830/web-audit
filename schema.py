import requests
import json
import extruct
from w3lib.html import get_base_url

SCHEMA_CHECKLIST = [
    ("Breadcrumbs", "BreadcrumbList"),
    ("FAQ", "FAQPage"),
    ("Article", "Article"),
    ("Video", "VideoObject"),
    ("Organization", "Organization"),
    ("How-to", "HowTo"),
    ("WebPage", "WebPage"),
    ("Product", "Product"),
    ("Review", "Review"),
    ("Person", "Person"),
    ("Event", "Event"),
    ("Recipe", "Recipe"),
    ("LocalBusiness", "LocalBusiness"),
    ("CreativeWork", "CreativeWork"),
    ("ItemList", "ItemList"),
    ("JobPosting", "JobPosting"),
    ("Course", "Course"),
    ("ImageObject", "ImageObject"),
    ("Service", "Service"),
]


def extract_schemas(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",  # Do Not Track request header
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status()
        base_url = get_base_url(response.text, response.url)

        data = extruct.extract(
            response.text, base_url=base_url, syntaxes=["json-ld", "microdata", "rdfa"]
        )
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return {} # Return empty data on error


def flatten_schema(schema_item):
    """Flatten nested schema items, including @graph structures."""
    if isinstance(schema_item, list):
        for item in schema_item:
            yield from flatten_schema(item)
    elif isinstance(schema_item, dict):
        if "@graph" in schema_item:
            yield from flatten_schema(schema_item["@graph"])
        yield schema_item


def extract_schema_names(schemas):
    schema_names = set()

    # Process JSON-LD schemas
    for item in flatten_schema(schemas.get("json-ld", [])):
        if "@type" in item:
            if isinstance(item["@type"], list):
                for t in item["@type"]:
                    schema_names.add(t)
            else:
                schema_names.add(item["@type"])

    # Process Microdata schemas
    for item in flatten_schema(schemas.get("microdata", [])):
        if "type" in item:
            if isinstance(item["type"], list):
                for t in item["type"]:
                    schema_names.add(t)
            else:
                schema_names.add(item["type"])

    # Process RDFa schemas
    for item in flatten_schema(schemas.get("rdfa", [])):
        if "type" in item: # RDFa often uses 'typeof' or similar, but extruct standardizes to 'type' here
            if isinstance(item["type"], list):
                for t in item["type"]:
                    schema_names.add(t)
            else:
                schema_names.add(item["type"])

    return sorted(schema_names)


def schema_implemented(schema_data, schema_type):
    for item in flatten_schema(schema_data):
        atype = item.get("@type", item.get("type", "")) # Check both @type and type
        if isinstance(atype, str) and atype.split('/')[-1].lower() == schema_type.lower():
            return True
        elif isinstance(atype, list):
            for t in atype:
                if isinstance(t, str) and t.split('/')[-1].lower() == schema_type.lower():
                    return True
    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract schema names (JSON-LD, Microdata, RDFa) from a webpage."
    )
    parser.add_argument("url", help="URL of the webpage to extract schema names from")
    parser.add_argument(
        "--full-schemas",
        action="store_true",
        help="Show full schema data instead of just names",
    )
    args = parser.parse_args()

    schemas = extract_schemas(args.url)
    if not schemas: # Handle cases where schema extraction fails
        print("Could not extract schemas.")
        return

    schema_names = extract_schema_names(schemas)

    print("\nSchema Names Found:")
    print("------------------")
    
    # --- MODIFICATION HERE ---
    processed_names_for_display = set()
    if schema_names:
        for name in schema_names:
            if isinstance(name, str): # Ensure name is a string
                short_name = name.split('/')[-1]
                processed_names_for_display.add(short_name)
            else:
                # Handle cases where name might not be a string (shouldn't happen with current extruct)
                processed_names_for_display.add(str(name)) 
        
        for short_name in sorted(list(processed_names_for_display)): # Sort for consistent output
            print(f"- {short_name}")
    else:
        print("No schema names found.")
    # --- END OF MODIFICATION ---

    print(f"\nTotal unique schema types (short names): {len(processed_names_for_display)}")

    if args.full_schemas:
        print("\nFull Schema Data:")
        print("----------------")
        print(json.dumps(schemas, indent=2))


if __name__ == "__main__":
    main()