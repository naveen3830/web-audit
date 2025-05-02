import streamlit as st
import csv
import requests
import pandas as pd
import io
from bs4 import BeautifulSoup
import base64
from datetime import datetime
import concurrent.futures
import time

st.set_page_config(page_title="SEO Header Analyzer", layout="wide")

st.title("SEO Header Analyzer")
st.markdown("Upload a CSV file with URLs to analyze header structure and identify common SEO issues.")

def get_urls_from_csv(csv_file):
    urls = []
    csv_content = csv_file.getvalue().decode('utf-8')
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    
    if not rows:
        return urls

    header = rows[0]
    if any("url" in cell.lower() for cell in header):
        url_index = header.index(next(cell for cell in header if "url" in cell.lower()))
        for row in rows[1:]:
            if row and len(row) > url_index:
                urls.append(row[url_index].strip())
    else:
        for row in rows:
            if row:
                urls.append(row[0].strip())
    return urls

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

st.sidebar.header("Options")

user_agent = st.sidebar.text_input(
    "User Agent (optional):",
    value="SEOHeaderAnalyzer/1.0"
)

st.sidebar.subheader("Threading Options")
max_workers = st.sidebar.slider(
    "Number of threads:",
    min_value=1,
    max_value=20,
    value=5,
    help="Higher numbers may speed up processing but could cause rate limiting on websites"
)


st.subheader("Upload CSV File")
uploaded_file = st.file_uploader("Choose a CSV file containing URLs", type="csv")

if uploaded_file is not None:
    urls = get_urls_from_csv(uploaded_file)
    
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

st.markdown("---")
st.markdown("SEO Header Analyzer | Built with Streamlit | Multithreaded Version")