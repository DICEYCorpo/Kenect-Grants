from dotenv import load_dotenv
import requests
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}
import os
import openai
import csv
load_dotenv()
from tqdm import tqdm
import pandas as pd
from bs4 import BeautifulSoup
import warnings
import numpy as np
# Suppress all warnings
warnings.filterwarnings("ignore")
with open("prompts.txt") as f:
    lines = f.read()


openai_api = os.getenv("OPENAIAPI")
openai.api_key = openai_api
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": lines}
    ]
)

gpt_response = response['choices'][0]['message']['content']

lines = [line.strip('#').strip() for line in gpt_response.strip().split('\n')]


extracted_links = {}
# Print each line
for line in lines:
    search_url = "https://api.bing.microsoft.com/v7.0/search"
    search_term = line + " intitle:Apply inbody:grant "
    sentence = line.split()
    location = sentence[-2]
    category = ' '.join(sentence[:-2])
    headers = {"Ocp-Apim-Subscription-Key": os.getenv("SUBKEY")}
    params = {"q": search_term, "textDecorations": True, "textFormat": "HTML", "answerCount": 6,
              'since': '2023-10-01'}
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()
    pages = (search_results['webPages'])
    results = pages['value']

    for result in results:
        url = result['url']
        snippets = result['snippet']
        name = result['name']
        if url not in extracted_links:
            extracted_links[url] = [name, snippets, location, category]

csv_file_path = 'extracted_links.csv'

# Writing to CSV file
with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.writer(csv_file)

    # Write header
    csv_writer.writerow(['Title', 'URL', 'Snippets', 'Location', 'Category', 'Award', 'Date'])

    # Write data
    for url, (name, snippets, location, category) in extracted_links.items():
        csv_writer.writerow([name, url, snippets, location, category])

print(f'Data has been written to {csv_file_path}')


headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'https://grants.gov',
    'Referer': 'https://grants.gov/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not A(Brand";v="99", "Brave";v="121", "Chromium";v="121"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

json_data = {
    'keyword': 'Educational, Vocational, Mental Health, STEM',
    'oppNum': None,
    'cfda': None,
    'agencies': None,
    'sortBy': '',
    'rows': 5000,
    'eligibilities': None,
    'fundingCategories': 'BC|ED|HL',
    'fundingInstruments': 'G',
    'dateRange': '',
    'oppStatuses': 'posted',
}

response = requests.post('https://apply07.grants.gov/grantsws/rest/opportunities/search', headers=headers, json=json_data)
json_extract = response.json()
opphits_ids = [opp["id"] for opp in json_extract["oppHits"]]
headers_new = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'Origin': 'https://grants.gov',
    'Referer': 'https://grants.gov/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not A(Brand";v="99", "Brave";v="121", "Chromium";v="121"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}
print(len(opphits_ids))
opportunity_data = []
for i in tqdm(opphits_ids, desc='Processing Opportunities'):
    data_i = {
        'oppId': i,
    }

    response = requests.post('https://apply07.grants.gov/grantsws/rest/opportunity/details', headers=headers_new,
                             data=data_i)


    try:
        data = response.json()
        opportunity_title = data.get('opportunityTitle')
        award_ceiling = data.get('synopsis', {}).get('awardCeiling')
        response_date = data.get('synopsis', {}).get('responseDate')
        category = data.get('synopsis', {}).get('fundingActivityCategories', [{}])[0].get('description')
        synopsis_desc = data.get('synopsis', {}).get('synopsisDesc')
        link = "https://grants.gov/search-results-detail/" + i
        location = 'Nationwide'

        # Append the data to the list
        opportunity_data.append([opportunity_title, link, synopsis_desc, location, category, award_ceiling, response_date])
    except KeyError:
        pass

csv_filename = "extracted_links.csv"


# Writing data to CSV file in append mode
with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
    csv_writer = csv.writer(csvfile)

    # Writing data
    csv_writer.writerows(opportunity_data)
# Read the CSV file into a DataFrame
df = pd.read_csv('extracted_links.csv')

# Function to clean HTML tags from a text
def clean_html_tags(text):
    soup = BeautifulSoup(text, 'html.parser')
    cleaned_text = soup.get_text()
    return cleaned_text

# Clean HTML tags from the 'Snippets' column
df['Snippets'] = df['Snippets'].apply(clean_html_tags)

# Clean HTML tags from the 'Title' column
df['Title'] = df['Title'].apply(clean_html_tags)

# Save the cleaned DataFrame to a new CSV file
df.to_csv('cleaned_file.csv', index=False)

print(f"Data has been cleaned and successfully appended to cleaned_file.csv")

# Read the CSV file into a DataFrame
df = pd.read_csv('cleaned_file.csv')

# Get the number of rows in the DataFrame
num_rows = df.shape[0]

# Generate a random permutation of row indices
random_indices = np.random.permutation(num_rows)

# Use the shuffled indices to reorder the DataFrame
df_shuffled = df.iloc[random_indices].reset_index(drop=True)

# Save the shuffled DataFrame back to the same CSV file
df_shuffled.to_csv('cleaned_file.csv', index=False)