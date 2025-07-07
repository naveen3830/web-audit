import streamlit as st
import requests
import json
import extruct
from w3lib.html import get_base_url
from urllib.parse import urlparse
import time
import pandas as pd
from typing import Dict, Set, List, Any, Tuple
from collections import defaultdict
import re

st.set_page_config(
    page_title="Debug Schema Markup Detector",
    page_icon="🐛",
    layout="wide"
)

def extract_schemas_with_debug(url: str, timeout: int = 10) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Extract schema markup from a given URL with debug information."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    debug_info = {
        "url": url,
        "response_status": None,
        "content_length": 0,
        "content_type": None,
        "json_ld_blocks": [],
        "microdata_elements": [],
        "rdfa_elements": [],
        "raw_html_sample": "",
        "extraction_errors": []
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        debug_info["response_status"] = response.status_code
        debug_info["content_length"] = len(response.text)
        debug_info["content_type"] = response.headers.get('content-type', 'unknown')
        debug_info["raw_html_sample"] = response.text[:2000]  # First 2000 chars
        
        # Manual extraction of JSON-LD blocks for debugging
        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        json_ld_matches = re.findall(json_ld_pattern, response.text, re.DOTALL | re.IGNORECASE)
        debug_info["json_ld_blocks"] = json_ld_matches
        
        # Check for microdata attributes
        microdata_patterns = [
            r'itemscope[^>]*',
            r'itemtype=["\'][^"\']*["\']',
            r'itemprop=["\'][^"\']*["\']'
        ]
        for pattern in microdata_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            debug_info["microdata_elements"].extend(matches)
        
        # Check for RDFa attributes
        rdfa_patterns = [
            r'typeof=["\'][^"\']*["\']',
            r'property=["\'][^"\']*["\']',
            r'resource=["\'][^"\']*["\']'
        ]
        for pattern in rdfa_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            debug_info["rdfa_elements"].extend(matches)
        
        base_url = get_base_url(response.text, response.url)
        
        # Use extruct to extract structured data
        try:
            data = extruct.extract(
                response.text, 
                base_url=base_url, 
                syntaxes=["json-ld", "microdata", "rdfa"],
                errors='ignore'  # Don't fail on malformed data
            )
        except Exception as e:
            debug_info["extraction_errors"].append(f"Extruct extraction error: {str(e)}")
            data = {"json-ld": [], "microdata": [], "rdfa": []}
        
        return data, debug_info
        
    except requests.exceptions.RequestException as e:
        debug_info["extraction_errors"].append(f"Request error: {str(e)}")
        st.error(f"Error fetching URL: {str(e)}")
        return None, debug_info

def manual_json_ld_parse(json_blocks: List[str]) -> List[Dict]:
    """Manually parse JSON-LD blocks to catch parsing issues."""
    parsed_blocks = []
    parsing_errors = []
    
    for i, block in enumerate(json_blocks):
        try:
            cleaned_block = block.strip()
            if cleaned_block:
                parsed = json.loads(cleaned_block)
                parsed_blocks.append({
                    "block_index": i,
                    "raw_content": cleaned_block[:500] + "..." if len(cleaned_block) > 500 else cleaned_block,
                    "parsed_data": parsed,
                    "parsing_success": True
                })
        except json.JSONDecodeError as e:
            parsing_errors.append({
                "block_index": i,
                "raw_content": cleaned_block[:500] + "..." if len(cleaned_block) > 500 else cleaned_block,
                "error": str(e),
                "parsing_success": False
            })
    
    return parsed_blocks, parsing_errors

def deep_inspect_object(obj: Any, path: str = "", max_depth: int = 10, current_depth: int = 0) -> List[Dict]:
    """Deep inspection of any object to find all nested structures."""
    findings = []
    
    if current_depth > max_depth:
        return findings
    
    if isinstance(obj, dict):
        # Record this object
        object_info = {
            "path": path or "root",
            "depth": current_depth,
            "type": "dict",
            "keys": list(obj.keys()),
            "has_type_field": "@type" in obj or "type" in obj,
            "type_values": []
        }
        
        # Extract type information
        if "@type" in obj:
            type_val = obj["@type"]
            if isinstance(type_val, list):
                object_info["type_values"].extend(type_val)
            else:
                object_info["type_values"].append(type_val)
        
        if "type" in obj:
            type_val = obj["type"]
            if isinstance(type_val, list):
                object_info["type_values"].extend(type_val)
            else:
                object_info["type_values"].append(type_val)
        
        findings.append(object_info)
        
        # Recursively inspect all values
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            findings.extend(deep_inspect_object(value, new_path, max_depth, current_depth + 1))
    
    elif isinstance(obj, list):
        findings.append({
            "path": path or "root",
            "depth": current_depth,
            "type": "list",
            "length": len(obj),
            "has_type_field": False,
            "type_values": []
        })
        
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            findings.extend(deep_inspect_object(item, new_path, max_depth, current_depth + 1))
    
    return findings

def normalize_url(url: str) -> str:
    """Normalize URL by adding https:// if not present."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

# Streamlit UI
st.title("🐛 Debug Schema Markup Detector")
st.markdown("**Deep debugging tool** - Find out exactly what's happening with schema extraction")

# Sidebar for settings
st.sidebar.header("Debug Settings")
timeout = st.sidebar.slider("Request Timeout (seconds)", 5, 30, 10)
max_inspection_depth = st.sidebar.slider("Max Inspection Depth", 5, 20, 15)
show_raw_html = st.sidebar.checkbox("Show Raw HTML Sample", False)
show_manual_parsing = st.sidebar.checkbox("Show Manual JSON-LD Parsing", True)
show_deep_inspection = st.sidebar.checkbox("Show Deep Object Inspection", True)

url_input = st.text_input(
    "Enter URL to debug:",
    placeholder="https://www.fortinet.com/solutions/enterprise-midsize-business/zero-trust-journey",
    help="Enter the URL that's not showing nested schemas correctly"
)

if st.button("🐛 Debug Schema Extraction", type="primary"):
    if url_input:
        normalized_url = normalize_url(url_input.strip())
        
        with st.spinner(f"Debugging schema extraction for: {normalized_url}"):
            start_time = time.time()
            schemas, debug_info = extract_schemas_with_debug(normalized_url, timeout)
            processing_time = time.time() - start_time
        
        st.success(f"🔍 Debug completed in {processing_time:.2f} seconds")
        
        # Debug Information Display
        st.header("🔧 Debug Information")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Response Status", debug_info.get("response_status", "Failed"))
        with col2:
            st.metric("Content Length", f"{debug_info.get('content_length', 0):,}")
        with col3:
            st.metric("Content Type", debug_info.get("content_type", "unknown"))
        with col4:
            json_ld_count = len(debug_info.get("json_ld_blocks", []))
            st.metric("JSON-LD Blocks Found", json_ld_count)
        
        # Show extraction errors
        if debug_info.get("extraction_errors"):
            st.error("❌ Extraction Errors:")
            for error in debug_info["extraction_errors"]:
                st.write(f"• {error}")
        
        # Manual JSON-LD Analysis
        if show_manual_parsing and debug_info.get("json_ld_blocks"):
            st.subheader("🔍 Manual JSON-LD Block Analysis")
            parsed_blocks, parsing_errors = manual_json_ld_parse(debug_info["json_ld_blocks"])
            
            if parsed_blocks:
                st.success(f"✅ Successfully parsed {len(parsed_blocks)} JSON-LD blocks")
                
                for block_info in parsed_blocks:
                    with st.expander(f"JSON-LD Block {block_info['block_index']} (Parsed Successfully)"):
                        st.json(block_info["parsed_data"])
                        
                        if show_deep_inspection:
                            st.write("**Deep Inspection Results:**")
                            inspection_results = deep_inspect_object(
                                block_info["parsed_data"], 
                                max_depth=max_inspection_depth
                            )
                            
                            # Show objects with type information
                            typed_objects = [r for r in inspection_results if r.get("has_type_field")]
                            if typed_objects:
                                st.write(f"Found {len(typed_objects)} objects with type information:")
                                for obj_info in typed_objects:
                                    st.write(f"• **Path:** `{obj_info['path']}` **Depth:** {obj_info['depth']} **Types:** {obj_info['type_values']}")
                            else:
                                st.write("❌ No objects with @type or type fields found in this block")
            
            if parsing_errors:
                st.error(f"❌ Failed to parse {len(parsing_errors)} JSON-LD blocks")
                for error_info in parsing_errors:
                    with st.expander(f"JSON-LD Block {error_info['block_index']} (Parse Error)"):
                        st.error(f"Parse Error: {error_info['error']}")
                        st.code(error_info["raw_content"])
        
        # Extruct Results Analysis
        if schemas:
            st.subheader("📊 Extruct Extraction Results")
            
            total_items = 0
            for markup_type in ["json-ld", "microdata", "rdfa"]:
                if schemas.get(markup_type):
                    count = len(schemas[markup_type])
                    total_items += count
                    st.write(f"**{markup_type.upper()}:** {count} items")
                    
                    if show_deep_inspection and count > 0:
                        with st.expander(f"Deep inspect {markup_type.upper()} data"):
                            inspection_results = deep_inspect_object(
                                schemas[markup_type], 
                                f"{markup_type}_root",
                                max_depth=max_inspection_depth
                            )
                            
                            # Show summary
                            typed_objects = [r for r in inspection_results if r.get("has_type_field")]
                            st.write(f"**Summary:** {len(inspection_results)} total objects, {len(typed_objects)} with type fields")
                            
                            # Show all typed objects
                            if typed_objects:
                                st.write("**Objects with Schema Types:**")
                                for obj_info in typed_objects:
                                    st.write(f"• `{obj_info['path']}` (depth {obj_info['depth']}): {obj_info['type_values']}")
                            
                            # Show full data
                            st.json(schemas[markup_type])
            
            if total_items == 0:
                st.warning("⚠️ Extruct found no structured data items")
        else:
            st.error("❌ Extruct extraction failed completely")
        
        # Microdata and RDFa Debug Info
        if debug_info.get("microdata_elements"):
            with st.expander(f"Microdata Elements Found ({len(debug_info['microdata_elements'])})"):
                for elem in debug_info["microdata_elements"][:20]:  # Show first 20
                    st.code(elem)
        
        if debug_info.get("rdfa_elements"):
            with st.expander(f"RDFa Elements Found ({len(debug_info['rdfa_elements'])})"):
                for elem in debug_info["rdfa_elements"][:20]:  # Show first 20
                    st.code(elem)
        
        # Raw HTML Sample
        if show_raw_html and debug_info.get("raw_html_sample"):
            with st.expander("Raw HTML Sample (First 2000 characters)"):
                st.code(debug_info["raw_html_sample"], language="html")
        
    else:
        st.warning("⚠️ Please enter a URL to debug.")

# Troubleshooting Guide
with st.expander("🚨 Troubleshooting Guide"):
    st.markdown("""
    **If nested schemas are not found, check:**
    
    1. **JSON-LD Parsing Errors**: Look for malformed JSON in the manual parsing section
    2. **Extruct vs Manual Results**: Compare what extruct finds vs manual JSON-LD parsing
    3. **Deep Inspection Results**: Check if objects with @type fields are actually present
    4. **Content Loading**: Some sites load schema data dynamically with JavaScript
    5. **Server Blocking**: Check if the site is blocking automated requests
    
    **Common Issues:**
    - **JavaScript-rendered schemas**: Extruct only processes static HTML, not JS-rendered content
    - **Malformed JSON**: Invalid JSON-LD blocks will be ignored by extruct
    - **Different attribute names**: Some sites use custom attributes instead of standard @type
    - **Deeply nested structures**: Very deep nesting might not be fully processed
    """)

st.markdown("---")
st.markdown("*Debug tool for schema markup detection issues*")