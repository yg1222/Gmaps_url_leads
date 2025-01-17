import os
from bs4 import BeautifulSoup
import lxml
import sys
import csv
import json
import pandas
import requests
import urllib.parse
from datetime import datetime
import re
import logging
from dotenv import load_dotenv

load_dotenv()
APIKey = os.getenv('key')
APIToken= os.getenv('token')
trello_list_id = os.getenv('list_id')
trello_label_id = os.getenv('label_id')

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s line %(lineno)s - %(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler("leads.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

    
def is_filtered_out(url):
    filter_out = [
        'google', 'gstatic', 'ggpht', 'schema.org', 'mapquest', 'w3.org', 'youtube',
        'facebook', 'twitter', 'amazon', 'github', 'js-agent', 'linkedin', 'instagram', 
        'pinterest', 'adservice', 'doubleclick', 'bing', 'apple', 'cloudflare', 
        'cdn', 'adobe', 'baidu', 'yahoo', 'tumblr', 'vimeo', 't.co', 'snapchat'
    ]
    keywords = ["contact", "about", "team", "staff", "leadership", "partners", "affiliates", "services", "products", "careers", "jobs", "press", "media", "support", "help", "customer-service", "investors", "news", "blog", "find-us", "reach-us", "get-in-touch", "feedback"]
    is_http = url.startswith("http")
    
    skip=True
    has_filter_tags = True
    has_keyword = False
    if any(sub in url for sub in keywords):
        has_keyword = True
            
    for x in filter_out:
        if x in url:
            has_filter_tags = True
    
    if is_http and has_keyword and not has_filter_tags:
        skip = False
        
    return skip
    
    
# Get all the internal links for a website 
def get_sub_urls(url, captured_urls=None):
    """
    Gets all the urls from a website
    
    :param str url: Website base url

    :rtype: set
    """ 
    if captured_urls is None:
        captured_urls = set()
    host_name = urllib.parse.urlparse(url).netloc
    if url in captured_urls:
        return     
    captured_urls.add(url) # adding the base url first
    try:
        res = requests.get(url)
    except Exception as err:
        logging.error(f"Failed opening {url} due to {err}")
        captured_urls.remove(url)
        return

    soup = BeautifulSoup(res.content, 'lxml')
    # get all its child urls    
    child_urls = set()
    

    try:
        links = soup.find_all('a', href=True)
        for link in links:
            if not is_filtered_out(link["href"]) and host_name in link["href"]: # restrict urls to hostmane's
                # logging.info(link["href"])
                child_urls.add(link["href"])
                # logging.info(f"child_urls size: {len(child_urls)}")
        # recursively capture
        for child_url in child_urls:
            get_sub_urls(child_url, captured_urls)
    except Exception as e:
            logging.error("Error. Skipping. "+e)
    
    return captured_urls


# Get all the email addresses from a webpage
def get_contacts_from_urls(website_pages):  
    """
    Gets all the email addresses from webpages from a url list. 
    Inteded to be pages from a single website.
    
    :param list website_pages: List of webpage urls
    :return emails: Set of email addresses

    :rtype: set
    """  
    if not website_pages:
        return None
    emails = set()
    phones = set()
    for link in website_pages:
        url_response = requests.get(link)
        content = url_response.content
        # Avoiding word documents
        content_type = url_response.headers.get('Content-Type', '').lower()
        # skip select content types
        if 'image/jpeg' in content_type:
            continue
        if not 'application/msword' in content_type or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            soup = BeautifulSoup(content, "html.parser")
            # sticking to using mailto rather than regex to avoid scraping junk email addresses 
            try:
                mailtos = soup.select('a[href^=mailto]')
                for mailto in mailtos:
                    if not str(mailto.string) == "None":
                        if "@" in mailto.string:
                            logging.info(f"Found '{mailto.string}' in '{link}'")
                            emails.add(mailto.string)
                            
                email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                found_emails = re.findall(email_regex, url_response.text)
                for email in found_emails:
                    logging.info(f"Found '{email}' via regex in '{link}'")
                    emails.add(email)
                    
            except UnicodeDecodeError as e:
                logging.error("Decoding error. Skipping. "+e)
            try:            
                tels = soup.select('a[href^=tel]')
                for tel in tels:                    
                    if not str(tel.string) == "None":
                        logging.info(f"Found '{tel.string}' in '{link}'")
                        phones.add(tel.string)

                phone_regex = r'\+?\d[\d\s\-\(\)]{9,}\d'
                found_phones = re.findall(phone_regex, url_response.text)
                for phone in found_phones:
                    logging.info(f"Found '{phone}' via regex in '{link}'")
                    phones.add(phone)
                    
            except UnicodeDecodeError as e:
                logging.error("Decoding error. Skipping. "+e)
        else:
            logging.info("This is a word document. Skipped.")

    return {
        "emails" : emails, 
        "phones" : phones,
    }

    
def get_page_title(home_url):
    try:
        res = requests.get(home_url)
        soup = BeautifulSoup(res.content, "html.parser")
        title = soup.find('title')
        return title.string
    except Exception as e:
        logging.error(f"Error occured trying to get page title: {e}")
        return None
                
                   
def main(): 
    leads_list = []    
    filtered_source_urls = set()
    # q = urllib.parse.quote(input("Search query (ie: coffee shops in New York): "))
    q = 'coffee shops in calgary'
    maps_url = input('Provide the google maps url of your search: ')
    # filter_in = input('Optional: Provide filters from the following comma separated examples ("without websites, without phone"): ')
    tag = input("What is the category of this leads list (ie: Gym owners, Software egency leads, etc): ")
    # maps_url='https://www.google.com/maps/search/web+developer+calgary/@51.0205974,-114.0766518,12z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI0MTAwOS4wIKXMDSoASAFQAw%3D%3D'
    # tag='Web Developer'
    # response_data = requests.get(f"https://www.google.com/maps/search/?api=1&query={q}")
    response_data = requests.get(maps_url)   
    if response_data.status_code == 200:        
        url_pattern = r'https?://[^\s/$.?#"]+(?:\\u[0-9A-Fa-f]{4})?[^\s"\\]+'
        urls = re.findall(url_pattern, response_data.content.decode('utf-8'))
        for url in urls:
            if not is_filtered_out(url):
                logging.info(f"Allowed {url} through the filter")
                filtered_source_urls.add(url)
            else:
                logging.info(f"Filtered out {url}")

        # logging.info(filtered_source_urls)
        for website in filtered_source_urls:
            logging.info(website)
            sub_urls = get_sub_urls(website)
            logging.info(f"\n{website} has -->  {sub_urls}")
            contacts = get_contacts_from_urls(sub_urls)
            lead = {
                'website': website,
                'name': get_page_title(website),                
                'phones': list(contacts['phones']) if contacts else "",
                'emails': list(contacts['emails']) if contacts else "",
                'category': tag
            }
            leads_list.append(lead)
        
        # current_time = datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
       
        # Return a json file
        current_time = datetime.now()
        if not os.path.exists("leads"):
            os.makedirs("leads")
        if not tag or tag =="":
            tag = "Leads"
        file_name_formatter = "leads/" + tag + "_" + current_time.strftime("%Y_%b_%d_%H%M%S")
        file_name = file_name_formatter+".json"
        with open(file_name, "w") as leads_file:
            json.dump(leads_list, leads_file, indent=4)

        # Return a csv file
        leads_json = json.dumps(leads_list)
        csv_str = pandas.read_json(leads_json)
        csv_str.to_csv(file_name_formatter + ".csv")

        push_json_to_trello(file_name)                
                
    else:
        return "Bad request"
    

def push_json_to_trello(leads_file):
    if not APIKey and APIToken:
        logging.info("No trello API key and token found.")
        return
    leads_list=None
    with open(leads_file, 'r') as f:
        leads_list = json.load(f)
    for lead in leads_list:
        # print(lead)
        # push to trello board
        try:
            url = "https://api.trello.com/1/cards"

            headers = {
                "Accept": "application/json"
            }
            phone_str = ""
            for x in lead['phones']:
                phone_str += "\n"+x
            email_str = ""
            for x in lead['emails']:
                email_str += "\n"+x
            query = {
                'idList': trello_list_id,
                'key': APIKey,
                'token': APIToken,
                'name': f"{lead['name']} - {lead['website']}",
                'desc': f"{lead['website']}{phone_str}{email_str}",
                'idLabels': trello_label_id
            }
            
            response = requests.request(
                "POST",
                url,
                headers=headers,
                params=query
            )            
            # print(response.content)
        except Exception as e:
            logging.error(f"Error creating trello cards: {e}")
      
                
if __name__ == '__main__':
    logging.info("\nNEW SESSION")
    main()
    # leads_file = "Leads_Software automation leads_2024_Oct_12_205336.json"
    # push_json_to_trello(leads_file)