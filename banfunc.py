import urllib.request
from html.parser import HTMLParser
import csv
from datetime import datetime
import os
import sys

CSV_FILENAME = "banned_functions.csv"

class MetaDateParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.last_modified = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attr_dict = dict(attrs)
            if attr_dict.get("name") == "updated_at":
                self.last_modified = attr_dict.get("content")

class BannedFunctionsTableParser(HTMLParser):
    def __init__(self, csv_filename, last_modified_date):
        super().__init__()
        self.inside_table = False
        self.inside_tr = False
        self.inside_code = False
        self.td_count = 0
        self.csv_file = open(csv_filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.current_row = []
        self.second_column_data = []

        # Write the last modified date as the first row
        self.csv_writer.writerow([last_modified_date.strftime("%Y-%m-%d %I:%M %p")])

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.inside_table = True
        elif tag == "tr" and self.inside_table:
            self.inside_tr = True
            self.td_count = 0
        elif tag == "td" and self.inside_tr:
            self.td_count += 1
        elif tag == "code" and self.inside_tr:
            self.inside_code = True

    def handle_data(self, data):
        if self.inside_code:
            if self.td_count == 1:
                self.current_row.append(data.strip())
            elif self.td_count == 2:
                self.second_column_data.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "table" and self.inside_table:
            self.inside_table = False
        elif tag == "tr" and self.inside_tr:
            if self.second_column_data:
                self.current_row.append(', '.join(self.second_column_data))
            if self.current_row:
                self.csv_writer.writerow(self.current_row)
            self.current_row = []
            self.second_column_data = []
            self.inside_tr = False
        elif tag == "code" and self.inside_code:
            self.inside_code = False

def read_previous_date_from_csv(filename):
    try:
        with open(filename, 'r', newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            first_row = next(csv_reader, None)
            if first_row:
                return datetime.strptime(first_row[0], "%Y-%m-%d %I:%M %p")
    except FileNotFoundError:
        print(f"WARNING: {CSV_FILENAME} not found. It will be created.")
    except Exception as e:
        print(f"ERROR: Unable to read the last-modified date from {CSV_FILENAME}. A new file will be created.")
        print(e)
    return None

def fetch_and_write_csv(url, csv_filename):
    html_content = None
    try:
        response = urllib.request.urlopen(url)
        html_content = response.read().decode("utf8")
        response.close()
    except:
        if os.path.isfile(CSV_FILENAME):
            print(f"ERROR: Unable to fetch the Microsoft Banned API Usage webpage. Using existing {CSV_FILENAME} instead.")
            return
        else:
            print(f"ERROR: Unable to fetch the Micorosft Banned API Usage webpage, and there is no existing {CSV_FILENAME}. Exiting.")
            sys.exit(1)
    
    meta_parser = MetaDateParser()
    meta_parser.feed(html_content)

    last_modified_date = None
    if meta_parser.last_modified:
        try:
            last_modified_date = datetime.strptime(meta_parser.last_modified, "%Y-%m-%d %I:%M %p")
        except ValueError as e:
            print(f"ERROR: Unable to parse the last-modified date from the Microsoft Banned API Usage webpage. A new {csv_filename} will be created.")
    else:
        print(f"ERROR: Unable to parse the last-modified date from the Microsoft Banned API Usage webpage. A new {csv_filename} will be created.")
    
    previous_csv_date = read_previous_date_from_csv(csv_filename)

    # Check if the csv needs to be updated
    if last_modified_date is None or previous_csv_date is None or last_modified_date > previous_csv_date:
        if (last_modified_date is not None 
            and previous_csv_date is not None 
            and last_modified_date > previous_csv_date
        ):
            print(f"{CSV_FILENAME} out of date: webpage last-modified - {last_modified_date}, csv date - {previous_csv_date}.")

        print(f"Creating a new {CSV_FILENAME}...")
        table_parser = BannedFunctionsTableParser(csv_filename, last_modified_date)
        table_parser.feed(html_content)
        table_parser.csv_file.close()
    else:
        print(f"{CSV_FILENAME} is up to date. Skipping csv creation.")

def banfunc():
    # Step 1: Web scraping to CSV, if CSV is outdated
    url = "https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/28719-banned-api-usage-use-updated-function-replacement"
    fetch_and_write_csv(url, CSV_FILENAME)
    
    # Step 2: Convert CSV to Python List to be returned
    print(f"Parsing {CSV_FILENAME}...")
    banned_functions = []
    with open(CSV_FILENAME, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        next(reader, None)  # Skip the first line, which contains the last-modified date
        for row in reader:
            key = row[0]
            if len(row) < 2:
                value = ""
            else:
                value = row[1]
            banned_functions.append({(key,): value})
    print(f"Successfully parsed {CSV_FILENAME}.")
    return banned_functions
