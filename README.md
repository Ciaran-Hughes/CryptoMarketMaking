# DataTrade
This code provides a complete framework from which to scrap/accumulate data from exchanges, provide liquidity  (market make) and make small profits in doing so, and then compute the profit vs. loss over time/assets. 

In essence:
Record data from a cryptocurrency exchange, use it to provide liquidity, and calculate the profit vs. loss. Makes profit by adding charge to each transaction to compensate for the risk of holding asset that buying. 


## Usage 

This code base is modular in order to reduce repeative code. There are three components of this code base: 
- Continuously record the trade history from an exchange in order to increase the size of the training data set (allowing more accurate predictions). This is done in the Record_Data/ folder. The './run_krak_record_bots.sh' bash script creates a tmux session for each market that you want to record. This bash script runs the python code in the Record_Data/ directory in order to ensure consistent and accurate data/formats over time. 
- The accumulated data can then be used used to train machine learning trading strategies. One of these strategies, based on the mid-spread, is included in the TraderBot/ directory. The KrakenMidSpreadController.py file is a bot which will use this strategy to provide liquidity to a market and make a small profit from each trade on average. You need to specify a market and the input scripts, and these can be found in the ETHXBT/folder. Copy these template files into the directory with the python scripts and then run 'python KrakenMidSpreadController.py'. 
- Compute your profit vs loss over time and ensure that the machine learning strategies are actually working as desired (i.e., the bot is not being taken advantage of by a malacious actor in the ecosystem, or the ML algorithm does not have undesired behaviors). This can be achieved with the 'python KrakenPnL.py' code. This will take in your historical trading history and compute the level of profit or loss across multiple assets and time. 


# Contributors
-Ciaran Hughes	iamciaran2@gmail.com
-Rian Hughes	rian.hughes@physics.ox.ac.uk

