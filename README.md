# StockWatcherAPI

<img src="http://investorplace.com/wp-content/uploads/2014/12/Nasdaq.jpg" />

Given 1 or more stock symbols, this API returns a Python dictionary where the key is a stock symbol and the value is another Python dictionary with all of the information about the stock. This sub-dictionary contains the financial data, headlines, and list of related companies for the corresponding stock symbol.

Note that this API will try to return as much information as possible - in other words, if there is an error in retrieving 1 bit of info, it will still try to return all others. If it can't retrieve anything at the moment, and the stock symbol is valid, then please try again; this means that the Yahoo servers weren't able to respond with the necessary info at that moment.

Visit <a href="https://api.blockspring.com/SaiWebApps/cd5a999185baa03ed10bdd30c13f25af">https://api.blockspring.com/SaiWebApps/cd5a999185baa03ed10bdd30c13f25af</a> to see the API in action.
