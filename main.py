from flask import Flask, render_template
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
import threading
import time
from getlink import scrape_website
from crawl import extract_data_from_div

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

first_request_made = False  # Flag to track if the first request has been made

class NewsModel:
    @staticmethod
    def find():
        return mongo.db.news.find()

    @staticmethod
    def insert_one(news):
        existing_news = mongo.db.news.find_one({"link": news["link"]})
        if existing_news:
            # If news with the same link already exists, don't insert again
            return
        mongo.db.news.insert_one(news)


def scrape_and_store(url):
    existing_urls = set(mongo.db.news.distinct("link"))
    data = scrape_website(url)
    hrefs = [link['href'] for link in data['links']]
    new_data = []

    for href in hrefs:
        if href in existing_urls:
            continue

        data_from_div = extract_data_from_div(href)
        if data_from_div.get('error'):
            print(f"Error extracting data from {href}: {data_from_div['error']}")
            continue
        
        news_model = {
            "link": href,
            "news": data_from_div['div_content_without_newlines'],
            "time": data_from_div['time']
        }
        NewsModel.insert_one(news_model)
        new_data.append(news_model)
        existing_urls.add(href)

    print(f"Response time: {time.time() / 60:.2f} minutes") 
    print(f"Thread data: {new_data}") 
    return new_data

def auto_scrape_and_update(url='https://www.sharesansar.com/category/latest'):
    while True:
        scrape_and_store(url)
        time.sleep(900)  #15 min

@app.route('/')
def get_data():
    global first_request_made
    if not first_request_made:
        first_request_made = True
        auto_scrape_thread = threading.Thread(target=auto_scrape_and_update)
        auto_scrape_thread.start()

    existing_data = list(NewsModel.find())
    
    all_data = existing_data
    all_data.sort(key=lambda x: x.get('time', float('-inf')), reverse=True)
    return render_template('index.html', data_list=all_data)

if __name__ == "__main__":
    app.run(debug=True)
