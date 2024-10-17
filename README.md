# Lead Scraper to Trello

This script scrapes leads (e.g., business listings from Google Maps) and creates Trello cards in a "Leads" list on a specified Trello board.

## Requirements

Install required packages:

```bash
pip install -r requirements.txt
```

## Setup
Create a .env file in the project root with your Trello API key and token:

```
key=your_trello_api_key
token=your_trello_api_token
list_id=your_trello_list_id
label_id=your_trello_label_id
```

Get Trello List ID: Use the Trello API to find the list ID for the "Leads" list:

```
GET https://api.trello.com/1/boards/{boardId}/lists?key={your_trello_api_key}&token={your_trello_api_token}
```
Or to get the list ID in Trello using the .json export, navigate to your Trello board and add .json at the end of the board's URL (e.g., https://trello.com/b/{boardId}.json). This will download the board's data in JSON format. In the JSON file, look for the lists section, which contains an array of lists on the board. Each list will have an id and a name field. Find the list with the name of your "Leads" list and copy its corresponding id, which you will use in your script to add cards programmatically.

## Usage
Run the script:
```
python leads.py
```

## Output
Each lead (business) scraped will be added as a Trello card with the business name as the title and contact info as the description.

## License
MIT License.
