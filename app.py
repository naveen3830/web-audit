import streamlit as st
import pandas as pd
import os
import re
import requests
import extruct
from w3lib.html import get_base_url
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from pathlib import Path

BASE_DIR = Path(__file__).parent

DATA_FILE_PATH = BASE_DIR / "Data" / "efax_internal_html.csv"
ALT_TAG_DATA_PATH = BASE_DIR / "Data" / "images_missing_alt_text_efax.csv"
ORPHAN_PAGES_DATA_PATH = BASE_DIR / "Data" / "efax_orphan_urls.csv"

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

URL_VARIATIONS = [
    "",
    "/about",
    "/about-us",
    "/products",
    "/services",
    "/solutions",
    "/blog",
    "/blogs",
    "/cyberglossary",
    "/news",
    "/resources",
    "/how-to",
    "/tutorials",
    "/guides",
    "/faq",
    "/help",
    "/support",
    "/contact",
    "/contact-us",
    "/reviews",
    "/testimonials",
    "/portfolio",
    "/cases",
    "/case-studies",
    "/team",
    "/careers",
    "/jobs",
    "/catalog",
    "/pricing",
    "/plans",
    "/login",
    "/signup",
    "/register",
]

def is_valid_page_url(url):
    if re.search(r'\.(jpg|jpeg|png|gif|bmp|pdf|doc|docx|xls|xlsx|css|js)$', url, re.IGNORECASE):
        return False
    if "wp-content" in url.lower() or "wp-uploads" in url.lower():
        return False
    return True

def extract_schemas(url, timeout=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        base_url = get_base_url(response.text, response.url)

        data = extruct.extract(
            response.text, base_url=base_url, syntaxes=["json-ld", "microdata", "rdfa"]
        )
        return data
    except requests.exceptions.RequestException:
        return None

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

    for item in flatten_schema(schemas.get("json-ld", [])):
        if "@type" in item:
            if isinstance(item["@type"], list):
                for t in item["@type"]:
                    schema_names.add(t)
            else:
                schema_names.add(item["@type"])

    for item in flatten_schema(schemas.get("microdata", [])):
        if "type" in item:
            if isinstance(item["type"], list):
                for t in item["type"]:
                    schema_names.add(t)
            else:
                schema_names.add(item["type"])

    for item in flatten_schema(schemas.get("rdfa", [])):
        if "type" in item:
            if isinstance(item["type"], list):
                for t in item["type"]:
                    schema_names.add(t)
            else:
                schema_names.add(item["type"])

    return sorted(schema_names)

def normalize_base_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_domain_from_df(df):
    """Extract domain from the first URL in the dataframe"""
    if df is not None and len(df) > 0 and "Address" in df.columns:
        first_url = df["Address"].iloc[0]
        if "://" in first_url:
            return first_url.split("/")[2]
        else:
            return first_url.split("/")[0]
    return None

def check_schema_markup(domain, max_workers=10, timeout=8):
    """Check schema markup for a domain using all URL variations"""
    base_url = normalize_base_url(domain)
    all_schemas = set()
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for variation in URL_VARIATIONS:
                full_url = urljoin(base_url, variation)
                future = executor.submit(extract_schemas, full_url, timeout)
                futures.append((future, full_url))
            
            for future, url in futures:
                try:
                    schemas = future.result(timeout=timeout + 2) 
                    if schemas:
                        schema_names = extract_schema_names(schemas)
                        all_schemas.update(schema_names)
                except Exception as e:
                    continue
                    
        return all_schemas
    except Exception as e:
        print(f"Error in check_schema_markup: {str(e)}")
        return set()
    
def update_schema_markup_analysis(df, report, expected_outcomes, sources):
    domain = get_domain_from_df(df)
    
    if domain:
        try:
            with st.spinner(f"Checking schema markup for {domain}... (this may take a moment)"):
                found_schemas = check_schema_markup(domain)
            
            if found_schemas:
                schema_list = sorted(list(found_schemas))
                current_value = f"Found {len(schema_list)} types: {', '.join(schema_list)}"

                if len(schema_list) >= 5:
                    status = "✅ Pass"
                elif len(schema_list) >= 2:
                    status = "ℹ️ Review"
                else:
                    status = "❌ Fail"
            else:
                current_value = "No schema markup detected"
                status = "❌ Fail"
                
        except Exception as e:
            current_value = f"Error checking schemas: {str(e)}"
            status = "ℹ️ Not Available"
            print(f"Schema analysis error: {str(e)}")
    else:
        current_value = "Cannot extract domain from data"
        status = "ℹ️ Not Available"
    
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Schema Markup")
    report["Current Value"].append(current_value)
    report["Expected Value"].append(expected_outcomes["Schema Markup"])
    report["Source"].append(sources["Schema Markup"])
    report["Status"].append(status)
    
def analyze_screaming_frog_data(df, alt_tag_df=None, orphan_pages_df=None):
    expected_outcomes = {
        "Website performance on desktop": "Score > 90",
        "Website performance on mobile": "Score > 80",
        "Core Web Vitals on desktop": "Pass",
        "Core Web Vitals on mobile": "Pass",
        "Accessibility Score": "Score > 90",
        "SEO Score": "Score > 90",
        "Mobile friendliness": "Pass",
        "Indexed pages": "All active pages are indexed",
        "Non indexed pages": "No active pages are in no index state.\nMinimal or no indexed pages",
        "Robots.txt file optimization": "Optimized",
        "Sitemap file optimization": "All active website URLs are part of sitemap",
        "Broken internal links (404)": "0 broken links",
        "Broken external links": "0 broken links",
        "Broken backlinks": "0 broken backlinks",
        "Broken Images": "0 broken Images",
        "Orphan page": "No orphan page",
        "Canonical Errors": "No page with canonical error",
        "Information architecture": "Site structure & navigation is well defined & easy to understand",
        "Header tags structure": "Content structure is well-defined and easy to understand",
        "Backlinks": "No of backlinks",
        "Domain authority": "DA >70",
        "Spam Score": "Score <5",
        "Duplicate content": "Minimal or no pages with issues",
        "Img alt tag": "Minimal or no pages with issues",
        "Duplicate & missing H1": "Minimal or no pages with issues",
        "Duplicate & missing meta title": "Minimal or no pages with issues",
        "Duplicate & missing description": "Minimal or no pages with issues",
        "Schema Markup": "Schema implementation opportunities",
    }

    sources = {
        "Website performance on desktop": "Pagespeedinsights",
        "Website performance on mobile": "Pagespeedinsights",
        "Core Web Vitals on desktop": "Pagespeedinsights",
        "Core Web Vitals on mobile": "Pagespeedinsights",
        "Accessibility Score": "Pagespeedinsights",
        "SEO Score": "Pagespeedinsights",
        "Mobile friendliness": "Manual",
        "Indexed pages": "Google search console",
        "Non indexed pages": "Google search console",
        "Robots.txt file optimization": "Manual",
        "Sitemap file optimization": "Manual",
        "Broken internal links (404)": "Ahrefs",
        "Broken external links": "Ahrefs",
        "Broken backlinks": "Ahrefs",
        "Broken Images": "Manual",
        "Orphan page": "Screamfrog",
        "Canonical Errors": "Screamfrog",
        "Information architecture": "Ahrefs",
        "Header tags structure": "Manual",
        "Backlinks": "Ahrefs",
        "Domain authority": "Moz",
        "Spam Score": "Moz",
        "Duplicate content": "Screamfrog",
        "Img alt tag": "Screamfrog",
        "Duplicate & missing H1": "Screamfrog",
        "Duplicate & missing meta title": "Screamfrog",
        "Duplicate & missing description": "Screamfrog",
        "Schema Markup": "Automated Schema Detection"
    }

    report = {
        "Category": [],
        "Parameters": [],
        "Current Value": [],
        "Expected Value": [],
        "Source": [],
        "Status": [],
    }

    performance_metrics = [
        "Website performance on desktop",
        "Website performance on mobile",
        "Core Web Vitals on desktop",
        "Core Web Vitals on mobile",
        "Accessibility Score",
        "SEO Score",
        "Mobile friendliness",
    ]

    for metric in performance_metrics:
        report["Category"].append("Performance & Core Web Vitals")
        report["Parameters"].append(metric)
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes[metric])
        report["Source"].append(sources[metric])
        report["Status"].append("ℹ️ Not Available")

    if "Indexability" in df.columns and "Indexability Status" in df.columns:
        indexed_pages = len(df[df["Indexability"] == "Indexable"])
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Indexed pages")
        report["Current Value"].append(indexed_pages)
        report["Expected Value"].append(expected_outcomes["Indexed pages"])
        report["Source"].append(sources["Indexed pages"])
        report["Status"].append("ℹ️ Review")

        non_indexed_pages = len(
            df[df["Indexability Status"].str.contains("noindex", na=False)]
        )
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Non indexed pages")
        report["Current Value"].append(non_indexed_pages)
        report["Expected Value"].append(expected_outcomes["Non indexed pages"])
        report["Source"].append(sources["Non indexed pages"])
        report["Status"].append("ℹ️ Review" if non_indexed_pages > 0 else "✅ Pass")
    else:
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Indexed pages")
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes["Indexed pages"])
        report["Source"].append(sources["Indexed pages"])
        report["Status"].append("ℹ️ Not Available")

        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Non indexed pages")
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes["Non indexed pages"])
        report["Source"].append(sources["Non indexed pages"])
        report["Status"].append("ℹ️ Not Available")

    report["Category"].append("Crawling & Indexing")
    report["Parameters"].append("Robots.txt file optimization")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Robots.txt file optimization"])
    report["Source"].append(sources["Robots.txt file optimization"])
    report["Status"].append("ℹ️ Not Available")

    report["Category"].append("Crawling & Indexing")
    report["Parameters"].append("Sitemap file optimization")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Sitemap file optimization"])
    report["Source"].append(sources["Sitemap file optimization"])
    report["Status"].append("ℹ️ Not Available")

    # Site Health & Structure
    broken_internal_links = len(df[df["Status Code"] == 404])
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken internal links (404)")
    report["Current Value"].append(broken_internal_links)
    report["Expected Value"].append(expected_outcomes["Broken internal links (404)"])
    report["Source"].append(sources["Broken internal links (404)"])
    report["Status"].append("❌ Fail" if broken_internal_links > 0 else "✅ Pass")

    # External links and backlinks (not available from Screaming Frog)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken external links")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Broken external links"])
    report["Source"].append(sources["Broken external links"])
    report["Status"].append("ℹ️ Not Available")

    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken backlinks")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Broken backlinks"])
    report["Source"].append(sources["Broken backlinks"])
    report["Status"].append("ℹ️ Not Available")

    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken Images")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Broken Images"])
    report["Source"].append(sources["Broken Images"])
    report["Status"].append("ℹ️ Not Available")

    # Orphan pages
    orphan_pages_count = 0
    if orphan_pages_df is not None and not orphan_pages_df.empty:
        orphan_pages_count = len(orphan_pages_df)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Orphan page")
    report["Current Value"].append(orphan_pages_count)
    report["Expected Value"].append(expected_outcomes["Orphan page"])
    report["Source"].append(sources["Orphan page"])
    report["Status"].append("❌ Fail" if orphan_pages_count > 0 else "✅ Pass")

    # Canonical Errors
    canonical_errors = len(df[df["Canonical Link Element 1"] != df["Address"]])
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Canonical Errors")
    report["Current Value"].append(canonical_errors)
    report["Expected Value"].append(expected_outcomes["Canonical Errors"])
    report["Source"].append(sources["Canonical Errors"])
    report["Status"].append("❌ Fail" if canonical_errors > 0 else "✅ Pass")

    # Information architecture and header tags structure (not available from Screaming Frog)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Information architecture")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Information architecture"])
    report["Source"].append(sources["Information architecture"])
    report["Status"].append("ℹ️ Not Available")

    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Header tags structure")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Header tags structure"])
    report["Source"].append(sources["Header tags structure"])
    report["Status"].append("ℹ️ Not Available")

    link_profile_metrics = ["Backlinks", "Domain authority", "Spam Score"]
    for metric in link_profile_metrics:
        report["Category"].append("Link Profile & Authority")
        report["Parameters"].append(metric)
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes[metric])
        report["Source"].append(sources[metric])
        report["Status"].append("ℹ️ Not Available")

    duplicate_content = 0
    if "Word Count" in df.columns and "Sentence Count" in df.columns:
        df_content = df[df["Word Count"].notna() & df["Sentence Count"].notna()]
        duplicate_content = len(
            df_content[
                df_content.duplicated(
                    subset=["Word Count", "Sentence Count"], keep=False
                )
            ]
        )
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Duplicate content")
    report["Current Value"].append(duplicate_content)
    report["Expected Value"].append(expected_outcomes["Duplicate content"])
    report["Source"].append(sources["Duplicate content"])
    report["Status"].append("❌ Fail" if duplicate_content > 0 else "✅ Pass")

    images_missing_alt_text = 0
    if alt_tag_df is not None and not alt_tag_df.empty:
        images_missing_alt_text = len(alt_tag_df)
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Img alt tag")
    report["Current Value"].append(images_missing_alt_text)
    report["Expected Value"].append(expected_outcomes["Img alt tag"])
    report["Source"].append(sources["Img alt tag"])
    report["Status"].append("❌ Fail" if images_missing_alt_text > 0 else "✅ Pass")

    missing_h1 = df["H1-1"].isna().sum()
    duplicate_h1 = len(df[df["H1-1"].duplicated(keep=False)])
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Duplicate & missing H1")
    report["Current Value"].append(f"Missing: {missing_h1}, Duplicate: {duplicate_h1}")
    report["Expected Value"].append(expected_outcomes["Duplicate & missing H1"])
    report["Source"].append(sources["Duplicate & missing H1"])
    report["Status"].append(
        "❌ Fail" if missing_h1 > 0 or duplicate_h1 > 0 else "✅ Pass"
    )

    missing_title = df["Title 1"].isna().sum()
    duplicate_titles = 0
    df_with_titles = df[df["Title 1"].notna() & (df["Title 1"] != "")]
    duplicate_titles = len(
        df_with_titles[df_with_titles["Title 1"].duplicated(keep=False)]
    )
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Duplicate & missing meta title")
    report["Current Value"].append(
        f"Missing: {missing_title}, Duplicate: {duplicate_titles}"
    )
    report["Expected Value"].append(expected_outcomes["Duplicate & missing meta title"])
    report["Source"].append(sources["Duplicate & missing meta title"])
    report["Status"].append(
        "❌ Fail" if missing_title > 0 or duplicate_titles > 0 else "✅ Pass"
    )

    # Meta description issues
    missing_description = df["Meta Description 1"].isna().sum()
    duplicate_descriptions = len(df[df["Meta Description 1"].duplicated(keep=False)])
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Duplicate & missing description")
    report["Current Value"].append(
        f"Missing: {missing_description}, Duplicate: {duplicate_descriptions}"
    )
    report["Expected Value"].append(
        expected_outcomes["Duplicate & missing description"]
    )
    report["Source"].append(sources["Duplicate & missing description"])
    report["Status"].append(
        "❌ Fail"
        if missing_description > 0 or duplicate_descriptions > 0
        else "✅ Pass"
    )
    update_schema_markup_analysis(df, report, expected_outcomes, sources)

    # Schema Markup (not available from Screaming Frog)
    # report["Category"].append("Metadata & Schema")
    # report["Parameters"].append("Schema Markup")
    # report["Current Value"].append("N/A")
    # report["Expected Value"].append(expected_outcomes["Schema Markup"])
    # report["Source"].append(sources["Schema Markup"])
    # report["Status"].append("ℹ️ Not Available")

    # Prepare detail data for deeper analysis
    duplicate_data = None
    if duplicate_titles > 0:
        duplicate_data = df_with_titles[
            df_with_titles["Title 1"].duplicated(keep=False)
        ][["Address", "Title 1", "Title 1 Length"]]

    duplicate_content_data = None
    if (
        duplicate_content > 0
        and "Word Count" in df.columns
        and "Sentence Count" in df.columns
    ):
        duplicate_content_data = df[
            df.duplicated(subset=["Word Count", "Sentence Count"], keep=False)
        ][["Address", "Word Count", "Sentence Count"]]

    h1_issues_data = None
    if missing_h1 > 0 or duplicate_h1 > 0:
        h1_issues_data = df[df["H1-1"].isna() | df["H1-1"].duplicated(keep=False)][
            ["Address", "H1-1"]
        ]
        h1_issues_data = h1_issues_data[h1_issues_data["Address"].apply(is_valid_page_url)]

    description_issues_data = None
    if missing_description > 0 or duplicate_descriptions > 0:
        description_issues_data = df[
            df["Meta Description 1"].isna()
            | df["Meta Description 1"].duplicated(keep=False)
        ][["Address", "Meta Description 1"]]
        description_issues_data = description_issues_data[description_issues_data["Address"].apply(is_valid_page_url)]

    final_report_df = pd.DataFrame(report)
    if not final_report_df.empty:
        final_report_df = final_report_df.set_index(["Category", "Parameters"])

    return final_report_df, {
        "duplicate_titles": duplicate_data,
        "duplicate_content": duplicate_content_data,
        "h1_issues": h1_issues_data,
        "description_issues": description_issues_data,
    }

def main():
    st.set_page_config(page_title="Web Audit Data Analyzer", layout="wide")

    st.title("Web Audit Data Analyzer")
    st.markdown(
        "A comprehensive analysis of your website's SEO health based on Screaming Frog data"
    )
    st.divider()

    try:
        file_option = st.radio(
            "Select data source", ["Use default file path", "Upload files"]
        )

        df = None
        alt_tag_df = None
        orphan_pages_df = None

        if file_option == "Upload files":
            st.info("You must upload all three files to proceed with the analysis")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("### Main Screaming Frog Data")
                main_file = st.file_uploader(
                    "Upload Screaming Frog CSV export", type="csv", key="main_file"
                )
                if main_file:
                    df = pd.read_csv(main_file)
                    st.success(f"✅ Main file uploaded with {len(df)} rows")
                else:
                    st.warning("Main file required")

            with col2:
                st.markdown("### Alt Tag Data")
                alt_tag_file = st.file_uploader(
                    "Upload Images Missing Alt Tags CSV", type="csv", key="alt_tag_file"
                )
                if alt_tag_file:
                    alt_tag_df = pd.read_csv(alt_tag_file)
                    st.success(f"✅ Alt tag file uploaded with {len(alt_tag_df)} rows")
                else:
                    st.warning("Alt tag file required")

            with col3:
                st.markdown("### Orphan Pages Data")
                orphan_file = st.file_uploader(
                    "Upload Orphan Pages CSV", type="csv", key="orphan_file"
                )
                if orphan_file:
                    orphan_pages_df = pd.read_csv(orphan_file)
                    st.success(
                        f"✅ Orphan pages file uploaded with {len(orphan_pages_df)} rows"
                    )
                else:
                    st.warning("Orphan pages file required")

            all_files_uploaded = (
                main_file is not None
                and alt_tag_file is not None
                and orphan_file is not None
            )

            if not all_files_uploaded:
                st.warning("Please upload all three required files to continue")
                return

            file_source = "uploaded files"

        else:
            if (
                os.path.exists(DATA_FILE_PATH)
                and os.path.exists(ALT_TAG_DATA_PATH)
                and os.path.exists(ORPHAN_PAGES_DATA_PATH)
            ):
                df = pd.read_csv(DATA_FILE_PATH)
                alt_tag_df = pd.read_csv(ALT_TAG_DATA_PATH)
                orphan_pages_df = pd.read_csv(ORPHAN_PAGES_DATA_PATH)
                file_source = "default file paths"
            else:
                missing_files = []
                if not os.path.exists(DATA_FILE_PATH):
                    missing_files.append(f"Main data file: {DATA_FILE_PATH}")
                if not os.path.exists(ALT_TAG_DATA_PATH):
                    missing_files.append(f"Alt tag data file: {ALT_TAG_DATA_PATH}")
                if not os.path.exists(ORPHAN_PAGES_DATA_PATH):
                    missing_files.append(
                        f"Orphan pages data file: {ORPHAN_PAGES_DATA_PATH}"
                    )

                st.error("The following files were not found at the default paths:")
                for file in missing_files:
                    st.error(f"- {file}")
                st.error("Please use the 'Upload files' option instead.")
                return

        st.divider()

        if df is not None and len(df) > 0:
            domain = (
                df["Address"].iloc[0].split("/")[2]
                if "://" in df["Address"].iloc[0]
                else df["Address"].iloc[0]
            )
            st.success(f"Website audit for the domain: {domain}")

            # Process the data button
            if st.button("Process Data and Generate Report", type="primary"):
                with st.spinner("Analyzing data and generating report..."):
                    st.divider()
                    report_df, detailed_data = analyze_screaming_frog_data(
                        df, alt_tag_df, orphan_pages_df
                    )

                    st.subheader("SEO Audit Results")
                    
                    def highlight_status(val):
                        if val == "✅ Pass":
                            return "background-color: #28a745; color: white;"    # Green
                        elif val == "❌ Fail":
                            return "background-color: #dc3545; color: white;"    # Red
                        elif val == "ℹ️ Review":
                            return "background-color: #ffc107; color: black;"    # Amber
                        elif val == "ℹ️ Not Available":
                            return "background-color: #D3D3D3; color: black;"    # Blue
                        else:
                            return ""

                    if not report_df.empty:
                        styled_df = report_df.style.applymap(
                            highlight_status,
                            subset=["Status"]
                        )
                        st.dataframe(styled_df, use_container_width=True)
                    else:
                        st.info("No report data to display.")
                    
                    st.divider()
                    st.subheader("Detailed Issues for Further Analysis")

                    detailed_tabs = [
                        key
                        for key, value in detailed_data.items()
                        if value is not None and not value.empty
                    ]

                    if detailed_tabs:
                        tabs = st.tabs(
                            [name.replace("_", " ").title() for name in detailed_tabs]
                        )

                        for i, tab_name in enumerate(detailed_tabs):
                            with tabs[i]:
                                st.dataframe(detailed_data[tab_name])
                    else:
                        st.info("No detailed issues found for further analysis.")

                    if alt_tag_df is not None and not alt_tag_df.empty:
                        st.subheader("Images Missing Alt Text")
                        st.dataframe(alt_tag_df)

                    if orphan_pages_df is not None and not orphan_pages_df.empty:
                        st.subheader("Orphan Pages")
                        st.dataframe(orphan_pages_df)
                        
                    if not report_df.empty:
                        export_df = report_df.reset_index()
                        export_df["Status"] = export_df["Status"].replace(
                            {
                                "✅ Pass": "Pass",
                                "❌ Fail": "Fail",
                                "ℹ️ Review": "Review",
                                "ℹ️ Not Available": "Not Available",
                            }
                        )

                        csv = export_df.to_csv(index=False)
                        st.download_button(
                            label="Download Full Report as CSV",
                            data=csv.encode("utf-8"),
                            file_name="seo_audit_report.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("No report data to export.")

            with st.expander("Preview Raw Data", expanded=False):
                tabs = st.tabs(["Main Data", "Alt Tag Data", "Orphan Pages Data"])

                with tabs[0]:
                    st.dataframe(df)

                with tabs[1]:
                    if alt_tag_df is not None:
                        st.dataframe(alt_tag_df)
                    else:
                        st.warning("Alt tag data not loaded")

                with tabs[2]:
                    if orphan_pages_df is not None:
                        st.dataframe(orphan_pages_df)
                    else:
                        st.warning("Orphan pages data not loaded")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error(
            "If you're seeing this error, please make sure your files are in the correct format and try again."
        )

if __name__ == "__main__":
    main()