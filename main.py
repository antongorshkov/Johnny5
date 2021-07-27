from flask import Flask, render_template, request
from random import choice
import json
import requests
import yfinance as yf
from requests import get
from json import loads
import re
import os
from serpapi import GoogleSearch
import wikipediaapi

web_site = Flask(__name__)

def get_wiki_about(link):
  parts = link.split('/')
  subject = parts[-1]
  wiki_wiki = wikipediaapi.Wikipedia('en')
  page_py = wiki_wiki.page(subject)
  return(page_py.summary)

def goog_result(message):
  params = {
    "q": message,
    "hl": "en",
    "gl": "us",
    "api_key": os.environ['Serpapi Key']
  }

  search = GoogleSearch(params)
  results = search.get_dict()
  web_site.logger.error(results)
  if 'answer_box' not in results:
    #lets go through organic results, find a wiki one, and use wiki API to get About snippet
    org_results = results['organic_results']
    for res in org_results:
      if 'wikipedia' in res['link']:
        return(get_wiki_about(res['link'])) 
    return('I googled and I wikied, but I just cannot find an answer, can you say it a different way please?')

  answer_box = results['answer_box']
  if 'list' in answer_box:
    response = answer_box['list'][0]
  elif 'weather' in answer_box:
    response = answer_box['weather'] + ', ' + answer_box['temperature'] + ' degrees' 
  elif 'snippet' in answer_box:
    response = answer_box['snippet']
  elif 'result' in answer_box:
    response = answer_box['result']
  elif 'answer' in answer_box:
    response = answer_box['answer']
  elif 'definitions' in answer_box:
    response = answer_box['definitions'][0]
  elif 'title' in answer_box:
    response = answer_box['title']
  else: response = "I'm at a loss of words here, but I'm still learning, what did you mean by that?"

  return(response)

def send_response(peer, response):
  url = "https://api.profilora.com/whatsapp/send-message"
  web_site.logger.error('Sending back' + response + ' to ' + peer)

  payload = json.dumps({
    "sender": os.environ['sender'],
    "to": peer,
    "message": response
  })

  headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic ' + os.environ['Profilora API Auth']
  }

  response = requests.request("POST", url, headers=headers, data=payload)
  return('ok')

def random_quote():
  response = get('http://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=en')
  return('{quoteText} - {quoteAuthor}'.format(**loads(response.text)))

def latest_stock_price(ticker):
  tickerData = yf.Ticker(ticker)
  price = str(tickerData.info['currentPrice']) 
  return(price)

def gen_response(message):
  #strip chars, leaving only letters
  message = message.replace("Hey Johnny5,","")
  message = message.replace("?","")
  #regex = re.compile('[^a-zA-Z ]')
  #message = regex.sub('', message)

  if "stock price" in message:
    word_list = message.split()
    return(latest_stock_price(word_list[-1]))
  
  if "quote" in message:
    return(random_quote())

  message = goog_result(message)

  return message

@web_site.route('/healthcheck')
def healthcheck():
  return('ok')

@web_site.route('/')
def index():
	return render_template('index.html')

@web_site.route('/message', methods = ['POST'])
def respond():
  data = request.json
  message_type = data['waData']['type']
  if message_type == 'MESSAGE_DELIVERED':
    return('ok')
  fromMe = data['waData']['waInfo']['fromMe']
  if fromMe:
    return('ok')

  message = data['waData']['waInfo']['message']['conversation']
  peer = data['waData']['waInfo']['peer']
  
  if "Hey Johnny5" not in message:
    return('ok')

  response = gen_response(message)

  return(send_response(peer,response))

@web_site.route('/user/', defaults={'username': None})
@web_site.route('/user/<username>')
def generate_user(username):
	if not username:
		username = request.args.get('username')

	if not username:
		return 'Sorry error something, malformed request.'

	return render_template('personal_user.html', user=username)

web_site.run(host='0.0.0.0', port=8080)