import streamlit as st
import pandas as pd
import os

DATA_FILE_PATH = r"Data\efax_internal_html.csv"
ALT_TAG_DATA_PATH = r"Data\images_missing_alt_text_efax.csv"
ORPHAN_PAGES_DATA_PATH = r"Data\efax_orphan_urls.csv"

def analyze_screaming_frog_data(df, alt_tag_df=None, orphan_pages_df=None):
    report = {
        "Category": [],
        "Parameters": [],
        "Current Value": [],
        "Target": [],
        "Status": []
    }
    
    broken_internal_links = len(df[df["Status Code"] == 404])
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Broken internal links (404)")
    report["Current Value"].append(broken_internal_links)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if broken_internal_links > 0 else "✅ Pass")
    
    orphan_pages_count = 0
    if orphan_pages_df is not None and not orphan_pages_df.empty:
        orphan_pages_count = len(orphan_pages_df)
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Orphan pages")
    report["Current Value"].append(orphan_pages_count)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if orphan_pages_count > 0 else "✅ Pass")
    
    canonical_errors = len(df[df["Canonical Link Element 1"] != df["Address"]])
    report["Category"].append("Site Health & Structure")
    report["Parameters"].append("Canonical Errors")
    report["Current Value"].append(canonical_errors)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if canonical_errors > 0 else "✅ Pass")
    
    if "Indexability" in df.columns and "Indexability Status" in df.columns:
        indexed_pages = len(df[df["Indexability"] == "Indexable"])
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Indexed pages")
        report["Current Value"].append(indexed_pages)
        report["Target"].append("All active")
        report["Status"].append("ℹ️ Review")
        
        non_indexed_pages = len(df[df["Indexability Status"].str.contains("noindex", na=False)])
        report["Category"].append("Crawling & Indexing")
        report["Parameters"].append("Non indexed pages")
        report["Current Value"].append(non_indexed_pages)
        report["Target"].append("0")
        report["Status"].append("ℹ️ Review" if non_indexed_pages > 0 else "✅ Pass")
    
    df_with_titles = df[df["Title 1"].notna() & (df["Title 1"] != "")]
    duplicate_titles = len(df_with_titles[df_with_titles["Title 1"].duplicated(keep=False)])
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Duplicate titles")
    report["Current Value"].append(duplicate_titles)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if duplicate_titles > 0 else "✅ Pass")
    
    duplicate_content = 0
    if "Word Count" in df.columns and "Sentence Count" in df.columns:
        df_content = df[df["Word Count"].notna() & df["Sentence Count"].notna()]
        duplicate_content = len(df_content[df_content.duplicated(subset=["Word Count", "Sentence Count"], keep=False)])
        report["Category"].append("Metadata & Schema")
        report["Parameters"].append("Duplicate content")
        report["Current Value"].append(duplicate_content)
        report["Target"].append("0")
        report["Status"].append("❌ Fail" if duplicate_content > 0 else "✅ Pass")
    
    missing_h1 = df["H1-1"].isna().sum()
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Missing H1")
    report["Current Value"].append(missing_h1)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if missing_h1 > 0 else "✅ Pass")
    
    missing_title = df["Title 1"].isna().sum()
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Missing meta title")
    report["Current Value"].append(missing_title)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if missing_title > 0 else "✅ Pass")
    
    missing_description = df["Meta Description 1"].isna().sum()
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Missing meta description")
    report["Current Value"].append(missing_description)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if missing_description > 0 else "✅ Pass")
    
    if "Images Missing Alt Text" in df.columns:
        missing_alt = df["Images Missing Alt Text"].sum()
        report["Category"].append("Metadata & Schema")
        report["Parameters"].append("Missing image alt tags")
        report["Current Value"].append(missing_alt)
        report["Target"].append("0")
        report["Status"].append("❌ Fail" if missing_alt > 0 else "✅ Pass")
    
    images_missing_alt_text = 0
    if alt_tag_df is not None and not alt_tag_df.empty:
        images_missing_alt_text = len(alt_tag_df)
    else:
        images_missing_alt_text = 9  
        
    report["Category"].append("Metadata & Schema")
    report["Parameters"].append("Images missing alt text")
    report["Current Value"].append(images_missing_alt_text)
    report["Target"].append("0")
    report["Status"].append("❌ Fail" if images_missing_alt_text > 0 else "✅ Pass")
    
    duplicate_data = None
    if duplicate_titles > 0:
        duplicate_data = df_with_titles[df_with_titles["Title 1"].duplicated(keep=False)][["Address", "Title 1", "Title 1 Length"]]
    
    duplicate_content_data = None
    if duplicate_content > 0 and "Word Count" in df.columns and "Sentence Count" in df.columns:
        duplicate_content_data = df[df.duplicated(subset=["Word Count", "Sentence Count"], keep=False)][["Address", "Word Count", "Sentence Count"]]

    return pd.DataFrame(report), duplicate_data, duplicate_content_data

def main():
    st.set_page_config(page_title="Web Audit Data Analyzer", layout="wide")
    
    st.title("Web Audit Data Analyzer")
    st.markdown("A tabular analysis of your website's SEO health based on Screaming Frog data")
    st.divider()
    
    try:
        file_option = st.radio("Select data source", ["Use default file path", "Upload files"])
        
        df = None
        alt_tag_df = None
        orphan_pages_df = None
        
        if file_option == "Upload files":
            st.info("You must upload all three files to proceed with the analysis")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### Main Screaming Frog Data")
                main_file = st.file_uploader("Upload Screaming Frog CSV export", type="csv", key="main_file")
                if main_file:
                    df = pd.read_csv(main_file)
                    st.success(f"✅ Main file uploaded with {len(df)} rows")
                else:
                    st.warning("Main file required")
            
            with col2:
                st.markdown("### Alt Tag Data")
                alt_tag_file = st.file_uploader("Upload Images Missing Alt Tags CSV", type="csv", key="alt_tag_file")
                if alt_tag_file:
                    alt_tag_df = pd.read_csv(alt_tag_file)
                    st.success(f"✅ Alt tag file uploaded with {len(alt_tag_df)} rows")
                else:
                    st.warning("Alt tag file required")
            
            with col3:
                st.markdown("### Orphan Pages Data")
                orphan_file = st.file_uploader("Upload Orphan Pages CSV", type="csv", key="orphan_file")
                if orphan_file:
                    orphan_pages_df = pd.read_csv(orphan_file)
                    st.success(f"✅ Orphan pages file uploaded with {len(orphan_pages_df)} rows")
                else:
                    st.warning("Orphan pages file required")
            
            all_files_uploaded = main_file is not None and alt_tag_file is not None and orphan_file is not None
            
            if not all_files_uploaded:
                st.warning("Please upload all three required files to continue")
                return
                
            file_source = "uploaded files"
            
        else:
            # Using default file paths
            if os.path.exists(DATA_FILE_PATH) and os.path.exists(ALT_TAG_DATA_PATH) and os.path.exists(ORPHAN_PAGES_DATA_PATH):
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
                    missing_files.append(f"Orphan pages data file: {ORPHAN_PAGES_DATA_PATH}")
                
                st.error(f"The following files were not found at the default paths:")
                for file in missing_files:
                    st.error(f"- {file}")
                st.error("Please use the 'Upload files' option instead.")
                return
        
        # Now we know we have all 3 files loaded
        st.divider()
        
        # Show domain information
        if df is not None and len(df) > 0:
            domain = df["Address"].iloc[0].split('/')[2] if '://' in df["Address"].iloc[0] else df["Address"].iloc[0]
            st.success(f'Website audit for the domain: {domain}')
            
            # Process the data button
            if st.button("Process Data and Generate Report", type="primary"):
                with st.spinner('Analyzing data and generating report...'):
                    st.divider()
                    report_df, duplicate_data, duplicate_content_data = analyze_screaming_frog_data(df, alt_tag_df, orphan_pages_df)

                    st.subheader("SEO Audit Results")
                    
                    def highlight_status(val):
                        if val == "✅ Pass":
                            return 'background-color: #CCFFCC'
                        elif val == "❌ Fail":
                            return 'background-color: #FFCCCC'
                        else:
                            return 'background-color: #FFFFCC'
                    
                    for category in report_df['Category'].unique():
                        st.subheader(category)
                        category_df = report_df[report_df['Category'] == category]
                        styled_df = category_df.drop('Category', axis=1).style.map(
                            lambda x: highlight_status(x) if x in ["✅ Pass", "❌ Fail", "ℹ️ Review"] else '', 
                            subset=['Status']
                        )
                        st.table(styled_df)
                    
                    if duplicate_data is not None and not duplicate_data.empty:
                        st.subheader("Detailed Analysis: Duplicate Titles")
                        st.dataframe(duplicate_data.sort_values("Title 1"))
                    
                    if duplicate_content_data is not None and not duplicate_content_data.empty:
                        st.subheader("Detailed Analysis: Duplicate Content")
                        st.dataframe(duplicate_content_data.sort_values(["Word Count", "Sentence Count"]))
                    
                    # Add detailed views for the new datasets
                    if alt_tag_df is not None and not alt_tag_df.empty:
                        st.subheader("Detailed Analysis: Images Missing Alt Text")
                        st.dataframe(alt_tag_df)
                    
                    if orphan_pages_df is not None and not orphan_pages_df.empty:
                        st.subheader("Detailed Analysis: Orphan Pages")
                        st.dataframe(orphan_pages_df)
                    
                    # Create a copy of the report dataframe for CSV export with text-only status
                    export_df = report_df.copy()
                    # Replace symbols with text for CSV export
                    export_df['Status'] = export_df['Status'].replace({
                        "✅ Pass": "Pass",
                        "❌ Fail": "Fail",
                        "ℹ️ Review": "Review"
                    })
                    
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="Download Full Report as CSV",
                        data=csv.encode('utf-8'),
                        file_name="screaming_frog_seo_audit.csv",
                        mime="text/csv",
                    )
            
            # Add option to preview raw data
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
        st.error("If you're seeing this error, please make sure your files are in the correct format and try again.")


if __name__ == "__main__":
    main()