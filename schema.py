import requests
import json
import extruct
from w3lib.html import get_base_url

def extract_schemas(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',  # Do Not Track request header
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    base_url = get_base_url(response.text, response.url)
    
    data = extruct.extract(
        response.text,
        base_url=base_url,
        syntaxes=['json-ld', 'microdata', 'rdfa']
    )
    return data

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Extract schema markups (JSON-LD, Microdata, RDFa) from a webpage."
    )
    parser.add_argument(
        'url',
        help='URL of the webpage to extract schema markups from'
    )
    args = parser.parse_args()
    
    schemas = extract_schemas(args.url)
    print(json.dumps(schemas, indent=2))

if __name__ == '__main__':
    main()