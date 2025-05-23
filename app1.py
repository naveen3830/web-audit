import streamlit as st
import pandas as pd
import csv
import requests
import io
from bs4 import BeautifulSoup
import concurrent.futures
import time
from datetime import datetime

DATA_FILE_PATH = r"D:\\LeadWalnut\\web-audit\\Data\\efax_internal_html.csv"

def analyze_seo_data(df):
    report = {}

    report["broken_internal_links"] = len(df[df["Status Code"] == 404])
    report["canonical_errors"] = len(
        df[df["Canonical Link Element 1"] != df["Address"]]
    )

    report["indexed_pages"] = len(df[df["Indexability"] == "Indexable"])
    report["non_indexed_pages"] = len(
        df[df["Indexability Status"].str.contains("noindex", na=False)]
    )

    report["duplicate_titles"] = len(df[df["Title 1"].duplicated(keep=False)])
    report["duplicate_meta_descriptions"] = len(df[df["Meta Description 1"].duplicated(keep=False)])
    report["missing_h1"] = df["H1-1"].isna().sum()

    return report

def identify_duplicate_content(df):
    required_columns = ["Address", "Title 1", "Title 1 Length"]
    if not all(col in df.columns for col in required_columns):
        st.error(f"Required columns {required_columns} not found in the CSV. Please check your file.")
        return pd.DataFrame()
    
    columns_to_include = ["Address", "Title 1", "Title 1 Length", "Title 1 Pixel Width"]
    if "Indexability" in df.columns:
        columns_to_include.append("Indexability")
    if "Indexability Status" in df.columns:
        columns_to_include.append("Indexability Status")
    
    title_data = df[columns_to_include].copy()
    title_data = title_data.dropna(subset=["Title 1", "Title 1 Length"])
    duplicate_titles = title_data[title_data.duplicated(["Title 1", "Title 1 Length"], keep=False)]

    duplicate_titles = duplicate_titles.sort_values(["Title 1", "Title 1 Length"])
    
    return duplicate_titles

def get_urls_from_csv(file_path):
    urls = []
    try:
        df = pd.read_csv(file_path)
        if "Address" in df.columns:
            urls = df["Address"].tolist()
        elif any("url" in col.lower() for col in df.columns):
            url_col = next(col for col in df.columns if "url" in col.lower())
            urls = df[url_col].tolist()
        else:
            urls = df.iloc[:, 0].tolist()

        urls = [url for url in urls if isinstance(url, str)]
        return urls
    except Exception as e:
        st.error(f"Error reading URLs from CSV: {str(e)}")
        return []

def extract_page_info(url, user_agent):
    headers = {'User-Agent': user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title Found"
        
        meta_description_tag = soup.find('meta', attrs={'name': 'description'})
        meta_description = (meta_description_tag.get('content').strip() 
                        if meta_description_tag and meta_description_tag.get('content')
                        else "No Meta Description Found")

        headers_list = []
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = header.get_text(strip=True)
            if text:
                headers_list.append((header.name.lower(), text))

        seo_issues = []
        h1_count = sum(1 for tag, _ in headers_list if tag == 'h1')

        if h1_count == 0:
            seo_issues.append("Missing H1")
        elif h1_count > 1:
            seo_issues.append(f"Multiple H1s found ({h1_count})")
        
        if headers_list and h1_count >= 1:
            first_tag = headers_list[0][0]
            if first_tag != 'h1':
                seo_issues.append("First header is not H1")
        
        previous_level = None
        for idx, (tag, text) in enumerate(headers_list):
            current_level = int(tag[1])
            if previous_level is not None:
                if previous_level == 1 and current_level == 4 and "listen here" in text.lower():
                    pass
                else:
                    if current_level > previous_level + 1:
                        seo_issues.append(f"Hierarchy jump from H{previous_level} to H{current_level} at position {idx+1}: '{text}'")
            previous_level = current_level

        header_entries = [f"{tag.upper()}: {text}" for tag, text in headers_list]
        header_structure = '\n'.join(header_entries)
        
        return url, title, meta_description, header_structure, seo_issues, ''
    except requests.exceptions.RequestException as e:
        return url, None, None, '', [], str(e)

def seo_health_check_tab():
    st.header("SEO Health Check")
    
    try:
        st.info(f"Loading data from: {DATA_FILE_PATH}")
        
        try:
            df = pd.read_csv(DATA_FILE_PATH)
            st.success(f"Successfully loaded data with {len(df)} rows and {len(df.columns)} columns")
            
            with st.expander("Preview Data"):
                st.dataframe(df.head())
            
            report = analyze_seo_data(df)
            
            st.subheader("SEO Health Check Report")

            with st.expander("Technical Health Parameters", expanded=True):
                col1, col2 = st.columns(2)
                col1.metric(
                    "Broken Internal Links",
                    report["broken_internal_links"],
                    help="Count of 404 errors",
                    delta_color="inverse",
                )
                col2.metric(
                    "Canonical Errors",
                    report["canonical_errors"],
                    help="Pages with incorrect canonical tags",
                    delta_color="inverse",
                )

            with st.expander("Crawling & Indexing"):
                col1, col2 = st.columns(2)
                col1.metric("Indexed Pages", report["indexed_pages"])
                col2.metric(
                    "Non-Indexed Pages", report["non_indexed_pages"], delta_color="inverse"
                )

            with st.expander("Content Health"):
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Duplicate Titles", report["duplicate_titles"], delta_color="inverse"
                )
                col2.metric(
                    "Duplicate Meta Descriptions",
                    report["duplicate_meta_descriptions"],
                    delta_color="inverse",
                )
                col3.metric("Missing H1 Tags", report["missing_h1"], delta_color="inverse")

            duplicate_content = identify_duplicate_content(df)
            
            with st.expander("Duplicate Title Analysis", expanded=True):
                if not duplicate_content.empty:
                    st.metric(
                        "Duplicate Titles (Same Title & Length)",
                        len(duplicate_content),
                        delta_color="inverse",
                        help="Pages with identical Title and Title Length"
                    )
                    
                    st.subheader("Duplicate Titles")
                    st.dataframe(duplicate_content[["Address", "Title 1", "Title 1 Length", "Title 1 Pixel Width"]])
                else:
                    st.info("No duplicate titles found in the dataset.")

            st.download_button(
                label="Download Full Report",
                data=pd.DataFrame.from_dict(report, orient="index")
                .to_csv()
                .encode("utf-8"),
                file_name="seo_health_report.csv",
                mime="text/csv",
            )
        except FileNotFoundError:
            st.error(f"File not found: {DATA_FILE_PATH}")
        except Exception as e:
            st.error(f"Error processing CSV file: {str(e)}")
            
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")

def header_analysis_tab():
    st.header("Header Analysis")
    st.markdown("This tab analyzes header structure from URLs in your dataset.")

    # Sidebar options
    with st.expander("Analysis Options"):
        user_agent = st.text_input(
            "User Agent (optional):",
            value="SEOHeaderAnalyzer/1.0"
        )
        
        max_workers = st.slider(
            "Number of threads:",
            min_value=1,
            max_value=20,
            value=10,
            help="Higher numbers may speed up processing but could cause rate limiting on websites"
        )

    # Get URLs directly from the file
    st.subheader("URL Analysis")
    
    if st.button("Load URLs from Data File"):
        try:
            urls = get_urls_from_csv(DATA_FILE_PATH)
            
            if not urls:
                st.error("No URLs found in the CSV file.")
            else:
                st.write(f"Found {len(urls)} URLs in the CSV file.")
                
                limit = st.slider("Limit number of URLs to analyze (0 for all):", 0, len(urls), min(10, len(urls)))
                if limit > 0:
                    urls = urls[:limit]
                    st.write(f"Analyzing {limit} URLs...")
                
                if st.button("Start Analysis"):
                    start_time = time.time()
                    
                    total_pages = len(urls)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_placeholder = st.empty()
                    
                    results = []
                    completed = 0
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_url = {executor.submit(extract_page_info, url, user_agent): url for url in urls}
                        pages_with_issues = 0
                        pages_without_issues = 0
                        duplicate_h1_count = 0
                        missing_h1_count = 0
                        incorrect_hierarchy_count = 0
                        error_count = 0
                        
                        for future in concurrent.futures.as_completed(future_to_url):
                            url, title, meta_description, header_structure, seo_issues, error = future.result()
                            
                            completed += 1
                            progress = completed / total_pages
                            progress_bar.progress(progress)
                            status_text.text(f"Processed {completed}/{total_pages} URLs ({int(progress*100)}%)")
                            
                            if error:
                                error_count += 1
                                pages_with_issues += 1
                            else:
                                if seo_issues:
                                    pages_with_issues += 1
                                    for issue in seo_issues:
                                        if "Missing H1" in issue:
                                            missing_h1_count += 1
                                        if "Multiple H1s" in issue:
                                            duplicate_h1_count += 1
                                        if "Hierarchy jump" in issue:
                                            incorrect_hierarchy_count += 1
                                else:
                                    pages_without_issues += 1
                            
                            results.append({
                                'URL': url,
                                'Title': title or '',
                                'Meta Description': meta_description or '',
                                'Header Structure': header_structure,
                                'SEO Issues': "; ".join(seo_issues) if seo_issues else "No issues",
                                'Error': error
                            })
                    
                    df = pd.DataFrame(results)
                    
                    elapsed_time = time.time() - start_time
                    
                    st.success(f"Analysis complete! Processed {total_pages} URLs in {elapsed_time:.2f} seconds")
                    
                    tab1, tab2 = st.tabs(["Summary", "Detailed Results"])
                    
                    with tab1:
                        st.subheader("SEO Header Analysis Summary")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Total Pages", total_pages)
                            st.metric("Pages Without Issues", pages_without_issues)
                            st.metric("Pages With Issues", pages_with_issues)
                            st.metric("Processing Time", f"{elapsed_time:.2f} seconds")
                        
                        with col2:
                            st.metric("Missing H1", missing_h1_count)
                            st.metric("Duplicate H1", duplicate_h1_count)
                            st.metric("Incorrect Hierarchy", incorrect_hierarchy_count)
                            st.metric("Error Processing", error_count)

                        if total_pages > 0:
                            st.subheader("Issues Distribution")

                            chart_data = pd.DataFrame({
                                'Issue Type': ['No Issues', 'Missing H1', 'Duplicate H1', 'Incorrect Hierarchy', 'Processing Errors'],
                                'Count': [pages_without_issues, missing_h1_count, duplicate_h1_count, incorrect_hierarchy_count, error_count]
                            })
                            
                            st.bar_chart(chart_data.set_index('Issue Type'))
                    
                    with tab2:
                        st.subheader("Detailed Results")
                        st.dataframe(df)
                    
                    st.markdown("### Download Results")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    csv = df.to_csv(index=False).encode()
                    st.download_button(
                        label="Download CSV File",
                        data=csv,
                        file_name=f"seo_header_analysis_{timestamp}.csv",
                        mime="text/csv"
                    )
        except Exception as e:
            st.error(f"Error loading URLs: {str(e)}")

def main():
    st.set_page_config(page_title="Web Audit Data Analyzer", layout="wide")
    
    st.title("Web Audit Data Analyzer")
    st.markdown("A toolkit for analyzing your website's SEO health")
    st.info(f"Analyzing data from: {DATA_FILE_PATH}")
    
    tab1, tab2 = st.tabs(["SEO Health Check", "Header Analysis"])
    
    with tab1:
        seo_health_check_tab()
    
    with tab2:
        header_analysis_tab()

if __name__ == "__main__":
    main()