from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import pandas as pd
import io
from typing import Optional, Dict, Any
import os
from pydantic import BaseModel

app = FastAPI(
    title="Web Audit Data Analyzer API",
    description="A comprehensive analysis of your website's SEO health based on Screaming Frog data",
    version="1.0.0"
)

# Default file paths
DATA_FILE_PATH = r"Data\efax_internal_html.csv"
ALT_TAG_DATA_PATH = r"Data\images_missing_alt_text_efax.csv"
ORPHAN_PAGES_DATA_PATH = r"Data\efax_orphan_urls.csv"

class AuditResponse(BaseModel):
    domain: str
    report: Dict[str, Any]
    detailed_issues: Dict[str, Any]
    summary: Dict[str, int]

def analyze_screaming_frog_data(df, alt_tag_df=None, orphan_pages_df=None):
    """
    Analyze the Screaming Frog data and return audit results
    """
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
        "Schema Markup":"Manual or AIO Tool"
    }

    report = {
        "Category": [],
        "Parameters": [],
        "Current Value": [],
        "Expected Value": [],
        "Source": [],
        "Status": [],
    }

    # Performance & Core Web Vitals (These are not available from Screaming Frog)
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
        report["Status"].append("Not Available")

    # Crawling & Indexing
    if "Indexability" in df.columns and "Indexability Status" in df.columns:
        indexed_pages = len(df[df["Indexability"] == "Indexable"])
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Indexed pages")
        report["Current Value"].append(indexed_pages)
        report["Expected Value"].append(expected_outcomes["Indexed pages"])
        report["Source"].append(sources["Indexed pages"])
        report["Status"].append("Review")

        non_indexed_pages = len(
            df[df["Indexability Status"].str.contains("noindex", na=False)]
        )
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Non indexed pages")
        report["Current Value"].append(non_indexed_pages)
        report["Expected Value"].append(expected_outcomes["Non indexed pages"])
        report["Source"].append(sources["Non indexed pages"])
        report["Status"].append("Review" if non_indexed_pages > 0 else "Pass")
    else:
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Indexed pages")
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes["Indexed pages"])
        report["Source"].append(sources["Indexed pages"])
        report["Status"].append("Not Available")

        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Non indexed pages")
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes["Non indexed pages"])
        report["Source"].append(sources["Non indexed pages"])
        report["Status"].append("Not Available")

    # Add Robots.txt and Sitemap (not available from Screaming Frog)
    report["Category"].append("Crawling & Indexing")
    report["Parameters"].append("Robots.txt file optimization")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Robots.txt file optimization"])
    report["Source"].append(sources["Robots.txt file optimization"])
    report["Status"].append("Not Available")

    report["Category"].append("Crawling & Indexing")
    report["Parameters"].append("Sitemap file optimization")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Sitemap file optimization"])
    report["Source"].append(sources["Sitemap file optimization"])
    report["Status"].append("Not Available")

    # Site Health & Structure
    broken_internal_links = len(df[df["Status Code"] == 404])
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken internal links (404)")
    report["Current Value"].append(broken_internal_links)
    report["Expected Value"].append(expected_outcomes["Broken internal links (404)"])
    report["Source"].append(sources["Broken internal links (404)"])
    report["Status"].append("Fail" if broken_internal_links > 0 else "Pass")

    # External links and backlinks (not available from Screaming Frog)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken external links")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Broken external links"])
    report["Source"].append(sources["Broken external links"])
    report["Status"].append("Not Available")

    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken backlinks")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Broken backlinks"])
    report["Source"].append(sources["Broken backlinks"])
    report["Status"].append("Not Available")

    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken Images")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Broken Images"])
    report["Source"].append(sources["Broken Images"])
    report["Status"].append("Not Available")

    # Orphan pages
    orphan_pages_count = 0
    if orphan_pages_df is not None and not orphan_pages_df.empty:
        orphan_pages_count = len(orphan_pages_df)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Orphan page")
    report["Current Value"].append(orphan_pages_count)
    report["Expected Value"].append(expected_outcomes["Orphan page"])
    report["Source"].append(sources["Orphan page"])
    report["Status"].append("Fail" if orphan_pages_count > 0 else "Pass")

    # Canonical Errors
    canonical_errors = len(df[df["Canonical Link Element 1"] != df["Address"]])
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Canonical Errors")
    report["Current Value"].append(canonical_errors)
    report["Expected Value"].append(expected_outcomes["Canonical Errors"])
    report["Source"].append(sources["Canonical Errors"])
    report["Status"].append("Fail" if canonical_errors > 0 else "Pass")

    # Information architecture and header tags structure (not available from Screaming Frog)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Information architecture")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Information architecture"])
    report["Source"].append(sources["Information architecture"])
    report["Status"].append("Not Available")

    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Header tags structure")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Header tags structure"])
    report["Source"].append(sources["Header tags structure"])
    report["Status"].append("Not Available")

    # Link Profile & Authority (not available from Screaming Frog)
    link_profile_metrics = ["Backlinks", "Domain authority", "Spam Score"]
    for metric in link_profile_metrics:
        report["Category"].append("Link Profile & Authority")
        report["Parameters"].append(metric)
        report["Current Value"].append("N/A")
        report["Expected Value"].append(expected_outcomes[metric])
        report["Source"].append(sources[metric])
        report["Status"].append("Not Available")

    # Metadata & Schema
    # Duplicate content
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
    report["Status"].append("Fail" if duplicate_content > 0 else "Pass")

    # Img alt tag
    images_missing_alt_text = 0
    if alt_tag_df is not None and not alt_tag_df.empty:
        images_missing_alt_text = len(alt_tag_df)
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Img alt tag")
    report["Current Value"].append(images_missing_alt_text)
    report["Expected Value"].append(expected_outcomes["Img alt tag"])
    report["Source"].append(sources["Img alt tag"])
    report["Status"].append("Fail" if images_missing_alt_text > 0 else "Pass")

    # H1 issues
    missing_h1 = df["H1-1"].isna().sum()
    duplicate_h1 = len(df[df["H1-1"].duplicated(keep=False)])
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Duplicate & missing H1")
    report["Current Value"].append(f"Missing: {missing_h1}, Duplicate: {duplicate_h1}")
    report["Expected Value"].append(expected_outcomes["Duplicate & missing H1"])
    report["Source"].append(sources["Duplicate & missing H1"])
    report["Status"].append(
        "Fail" if missing_h1 > 0 or duplicate_h1 > 0 else "Pass"
    )

    # Meta title issues
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
        "Fail" if missing_title > 0 or duplicate_titles > 0 else "Pass"
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
        "Fail"
        if missing_description > 0 or duplicate_descriptions > 0
        else "Pass"
    )

    # Schema Markup (not available from Screaming Frog)
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Schema Markup")
    report["Current Value"].append("N/A")
    report["Expected Value"].append(expected_outcomes["Schema Markup"])
    report["Source"].append(sources["Schema Markup"])
    report["Status"].append("Not Available")

    # Prepare detail data for deeper analysis
    duplicate_data = None
    if duplicate_titles > 0:
        duplicate_data = df_with_titles[
            df_with_titles["Title 1"].duplicated(keep=False)
        ][["Address", "Title 1", "Title 1 Length"]].to_dict('records')

    duplicate_content_data = None
    if (
        duplicate_content > 0
        and "Word Count" in df.columns
        and "Sentence Count" in df.columns
    ):
        duplicate_content_data = df[
            df.duplicated(subset=["Word Count", "Sentence Count"], keep=False)
        ][["Address", "Word Count", "Sentence Count"]].to_dict('records')

    h1_issues_data = None
    if missing_h1 > 0 or duplicate_h1 > 0:
        h1_issues_data = df[df["H1-1"].isna() | df["H1-1"].duplicated(keep=False)][
            ["Address", "H1-1"]
        ].to_dict('records')

    description_issues_data = None
    if missing_description > 0 or duplicate_descriptions > 0:
        description_issues_data = df[
            df["Meta Description 1"].isna()
            | df["Meta Description 1"].duplicated(keep=False)
        ][["Address", "Meta Description 1"]].to_dict('records')

    # Convert orphan pages and alt tag data to dict
    orphan_pages_data = None
    if orphan_pages_df is not None and not orphan_pages_df.empty:
        orphan_pages_data = orphan_pages_df.to_dict('records')

    alt_tag_data = None
    if alt_tag_df is not None and not alt_tag_df.empty:
        alt_tag_data = alt_tag_df.to_dict('records')

    final_report_df = pd.DataFrame(report)
    
    return final_report_df.to_dict('records'), {
        "duplicate_titles": duplicate_data,
        "duplicate_content": duplicate_content_data,
        "h1_issues": h1_issues_data,
        "description_issues": description_issues_data,
        "orphan_pages": orphan_pages_data,
        "images_missing_alt_text": alt_tag_data,
    }

@app.get("/")
async def root():
    return {"message": "Web Audit Data Analyzer API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/analyze/upload", response_model=AuditResponse)
async def analyze_uploaded_files(
    main_file: UploadFile = File(..., description="Main Screaming Frog CSV export"),
    alt_tag_file: UploadFile = File(..., description="Images Missing Alt Tags CSV"),
    orphan_file: UploadFile = File(..., description="Orphan Pages CSV")
):
    """
    Analyze uploaded CSV files and return SEO audit results
    """
    try:
        # Read uploaded files
        main_content = await main_file.read()
        alt_tag_content = await alt_tag_file.read()
        orphan_content = await orphan_file.read()
        
        # Convert to DataFrames
        df = pd.read_csv(io.StringIO(main_content.decode('utf-8')))
        alt_tag_df = pd.read_csv(io.StringIO(alt_tag_content.decode('utf-8')))
        orphan_pages_df = pd.read_csv(io.StringIO(orphan_content.decode('utf-8')))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Main CSV file is empty")
        
        # Extract domain
        domain = (
            df["Address"].iloc[0].split("/")[2]
            if "://" in df["Address"].iloc[0]
            else df["Address"].iloc[0]
        )
        
        # Analyze data
        report, detailed_data = analyze_screaming_frog_data(df, alt_tag_df, orphan_pages_df)
        
        # Calculate summary statistics
        status_counts = {}
        for item in report:
            status = item["Status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return AuditResponse(
            domain=domain,
            report=report,
            detailed_issues=detailed_data,
            summary=status_counts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

@app.post("/analyze/default")
async def analyze_default_files():
    """
    Analyze files from default file paths and return SEO audit results
    """
    try:
        # Check if default files exist
        if not all([
            os.path.exists(DATA_FILE_PATH),
            os.path.exists(ALT_TAG_DATA_PATH), 
            os.path.exists(ORPHAN_PAGES_DATA_PATH)
        ]):
            missing_files = []
            if not os.path.exists(DATA_FILE_PATH):
                missing_files.append(f"Main data file: {DATA_FILE_PATH}")
            if not os.path.exists(ALT_TAG_DATA_PATH):
                missing_files.append(f"Alt tag data file: {ALT_TAG_DATA_PATH}")
            if not os.path.exists(ORPHAN_PAGES_DATA_PATH):
                missing_files.append(f"Orphan pages data file: {ORPHAN_PAGES_DATA_PATH}")
            
            raise HTTPException(
                status_code=404, 
                detail=f"Default files not found: {', '.join(missing_files)}"
            )
        
        # Load files
        df = pd.read_csv(DATA_FILE_PATH)
        alt_tag_df = pd.read_csv(ALT_TAG_DATA_PATH)
        orphan_pages_df = pd.read_csv(ORPHAN_PAGES_DATA_PATH)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Main CSV file is empty")
        
        # Extract domain
        domain = (
            df["Address"].iloc[0].split("/")[2]
            if "://" in df["Address"].iloc[0]
            else df["Address"].iloc[0]
        )
        
        # Analyze data
        report, detailed_data = analyze_screaming_frog_data(df, alt_tag_df, orphan_pages_df)
        
        # Calculate summary statistics
        status_counts = {}
        for item in report:
            status = item["Status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return AuditResponse(
            domain=domain,
            report=report,
            detailed_issues=detailed_data,
            summary=status_counts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

@app.get("/report/csv/{domain}")
async def download_csv_report(domain: str):
    """
    Download the audit report as CSV (placeholder - requires storing results)
    """
    # Note: In a real implementation, you'd need to store the results 
    # (e.g., in a database) and retrieve them here
    raise HTTPException(
        status_code=501, 
        detail="CSV download requires result storage implementation"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)