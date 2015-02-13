import urllib2
import json
import re
import blockspring

# BEGIN HELPER FUNCTIONS

def _get_page_json_data(url):
	'''
		Retrieve the contents at the specified "url," and convert them from 
		JSON format to a Python dict. Note that this function assumes that the 
		contents at "url" are in JSON format.

		Return None if something goes wrong.
	'''
	try:
		response = urllib2.urlopen(url).read()
		return json.loads(response)
	except:
		return None


def _get_url(symbol_list):
	'''
		Helper method for _fetch_financials. Returns URL indicating where 
		info about stocks in "symbol_list" can be found.
	'''
	# YQL API for Yahoo Finance Quotes
	URL_HEAD = 'https://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20yahoo.finance.quotes%20where%20symbol%20in%20('
	URL_TAIL = ')&format=json&env=store%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback='

	symbols_in_quotes = map(lambda elem: '\"' + elem + '\"', symbol_list)
	encoded = ','.join(symbols_in_quotes).strip(',')
	return ''.join([URL_HEAD, urllib2.quote(encoded), URL_TAIL])


def _remove_html_tags(json_data):
	'''
		Helper method that filters out the HTML tags within the JSON financial
		data in _fetch_financials. 
	'''
	for data_dict in json_data:
		for key in data_dict:
			if not data_dict[key]:
				continue
			data_dict[key] = re.sub('<[^>]*>', '', data_dict[key])


def _fetch_financials(symbol_list):
	'''
		Return a list of dictionaries containing financial data about 
		the companies specified in "symbol_list." If there is an error,
		return None.
	'''
	# Get the information.
	url = _get_url(symbol_list)
	all_info = _get_page_json_data(url)
	if not all_info or not all_info['query'] or not all_info['query']['results'] or \
			not all_info['query']['results']['quote']:
		return None
	
	# json_stock_info['query']['results']['quote'] will be a single dict if client
	# requested data for 1 company alone or a list of dicts if client requested
	# data for multiple companies.
	json_stock_info = all_info['query']['results']['quote']
	# So, if json_stock_info is a dict, add to a list, and then return the list. Otherwise, return as is.
	output = json_stock_info if len(symbol_list) > 1 else [json_stock_info]
	_remove_html_tags(output)
	return output


def _fetch_headlines(symbol_list):
	'''
		Fetch the headlines for each company in "symbol_list" from its respective
		Yahoo Finance profile page. Return a dict, where the key is the company symbol
		and the value is another dict containing the headlines' hyperlinks and contents
		(mapped to the key 'headlines_href' and 'headlines_content' respectively).
	'''
	URL_HEAD = "https://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20html%20where%20url%3D'http%3A%2F%2Ffinance.yahoo.com%2Fq%3Fs%3D"
	URL_TAIL = "'%20and%20xpath%3D'%2F%2Fdiv%5B%40id%3D%22yfi_headlines%22%5D%2Fdiv%5B2%5D%2Ful%2Fli%2Fa'&format=json&callback="

	headlines_map = {} # Key = company, value = list of headlines for that company

	# For each specified symbol, retrieve the headlines from Yahoo Finance, and add
	# a dict entry (company symbol, {'headlines_href': list of headlines' hyperlinks, 
	# 'headlines_content': list of headlines' content}).
	for symbol in symbol_list:
		url = ''.join([URL_HEAD, symbol, URL_TAIL])
		all_info = _get_page_json_data(url)
		if not all_info or not all_info.get('query', None) or not all_info['query'].get('results', None) \
				or not all_info['query']['results'].get('a', None):
			continue

		# headlines = list of dicts with 2 keys: href (headlines' hyperlinks) and
		# content (headlines' textual contents)
		headlines = all_info['query']['results']['a']
		headlines_href = map(lambda elem: elem['href'], headlines)
		headlines_contents = map(lambda elem: elem['content'], headlines)
		headlines_map[symbol] = {'headlines_href': headlines_href, 'headlines_content': headlines_contents}
	
	return headlines_map


def _fetch_related_companies(symbol_list):
	'''
		Return a dict, where the key is a company symbol from 'symbol_list' and
		the value is a list of related companies' symbols.
	'''
	URL_HEAD = "https://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20html%20where\%20url%3D'http%3A%2F%2Ffinance.yahoo.com%2Fq%3Fs%3D"
	URL_TAIL = "'%20and%20xpath%3D'%2F%2Fdiv%5B%40id%3D%22yfi_related_tickers%22%5D%2Fp%2Fspan%2Fa%2Fstrong'&format=json&callback="

	related_companies_map = {}
	for symbol in symbol_list:
		json_data = _get_page_json_data(''.join([URL_HEAD, symbol, URL_TAIL]))
		if not json_data or not json_data.get('query', None) or not json_data['query'].get('results', None) \
				or not json_data['query']['results'].get('strong', None):
			continue
		related_companies_list = json_data['query']['results']['strong']
		related_companies_map[symbol] = related_companies_list

	return related_companies_map


def _add_related_companies_to_aggregate_data(aggregate_map, related_companies_map):
	'''
		Helper method that synthesizes the data gathered by _fetch_headlines with
		_fetch_related_companies' data.
		aggregate_map: contains headlines data, key = symbol, value = dict w/ headlines info; 
			will contain integrated results
		related_companies_map: key = symbol, value = list of related companies
	'''
	if not related_companies_map:
		return
	for symbol in related_companies_map:
		aggregate_map[symbol]['related_companies'] = related_companies_map[symbol]


def _add_financial_data_to_aggregate_data(aggregate_map, financials_map):
	'''
		Helper method that synthesizes the data gathered by _fetch_financials with
		the data gathered from the other _fetch helpers.
	'''
	if not financials_map:
		return None

	# data_dict = list of dicts, where each dict has financial stats about a company (symbol)
	# all_data = dict where key = company symbol, value = dict with headlines' info + related companies list
	# Merge financials dict with all_data[company symbol].
	for data_dict in financials_map:
		# Pop 'symbol' & 'Symbol' since all_data already captures this info in the key.
		symbol = data_dict.pop('symbol', None)
		del data_dict['Symbol']
		if not symbol in aggregate_map:
			continue
		aggregate_map[symbol].update(data_dict)

# END HELPER FUNCTIONS


# BEGIN CLIENT-FACING (API) FUNCTIONS

def get_current_data(symbol_list):
	'''
		If successful, return a list of dicts, where each dict contains information about the
		companies specified in "symbol_list." If error, then return None.
		Company info gathered from Yahoo Finance, consists of headlines, financials, and related companies.
	'''
	if not symbol_list:
		return None

	all_data = _fetch_headlines(symbol_list)
	if not all_data:
		all_data = dict((symbol, {}) for symbol in symbol_list)

	_add_related_companies_to_aggregate_data(all_data, _fetch_related_companies(symbol_list))
	_add_financial_data_to_aggregate_data(all_data, _fetch_financials(symbol_list))
	return all_data

# END CLIENT-FACING (API) FUNCTIONS

def block(request, response):
	symbols_string = request.params.get('symbols', None)
	if not symbols_string:
		response.addOutput('stock_info', 'Please enter at least 1 valid stock symbol.')
		response.end()
		return
    
	symbols_list = [symbol.strip() for symbol in symbols_string.split(',')]
	output = get_current_data(symbols_list)
	if not output:
		output = 'Oops! There was an error in retrieving and synthesizing the stock info. Please try again.'
	response.addOutput('stock_info', output)
	response.end()

blockspring.define(block)
