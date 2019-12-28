"""
Description: Script to find out the profit vs. loss of all the 
             trades made over time. Then make pretty plots of them 
             to visualise. 

Author: Ciaran Hughes  <http://mailto:iamciaran2@gmail.com>
Author: Rian   Hughes  <http://mailto:rian.hughes@physics.ox.ac.uk>
Date  : August 2018
Version: 1.0.1
Maintainers: Authors
Status: Production

"""

#Import relevant modules
from __future__ import division 
import sys
import os
import time
import argparse
import traceback
import numpy as np
import matplotlib.pyplot as plt

#Import the modules needed for Kracken API
import krakenex
from pykrakenapi import KrakenAPI

#Import the modules needed for data IO
import pandas as pd
import json

#Custom made modules
sys.path.append("../../../..")
#Need to point the TraderBot to the FileBot
sys.path.append("../../../../FileBot/")
import BotFile
#from filename import class
from KrakenMidSpread import KrakenMidSpread
import Utils as utl

#################################### Main program #######################
def main():
    """Run the code to calculate profit vs loss and then plot it. 
                    
        Args:                                                                                            
            -None
        Returns:                                                                                         
            -Nothing returned.                                                                                            
     """
        

    #Read in prices need to gauge profit
    mrk1mrkt2_file = "PDNS-midspread_kraken_ethbtc.csv"
    mrk1usd_file = "PDNS-midspread_kraken_ethusd.csv" 
    mrk2usd_file = "PDNS-midspread_kraken_btcusd.csv"

    #Put into a dataframe
    m1m2_prices  = Read_Price_CSV(mrk1mrkt2_file)
    m1usd_prices = Read_Price_CSV(mrk1usd_file)
    m2usd_prices = Read_Price_CSV(mrk2usd_file)
    
    #Get history from website: Doesn't work as need permission
    url = "https://www.kraken.com/u/history/export?a=dl&k=SVBG"

    #The file location that has the trades
    #with filename as this try 
    filename="PDNS-trades.csv"
    
    #Read in CSV history
    trades = Read_In_Kraken_History_CSV(filename)

    #Add in API trade history (only 50 most recent)
    trades = Add_In_API_Trades(controller, trades)

    #Turn table into format we need 
    trades = Clean_Up_Trades_Book(local_settings, trades)
    
    #Add in account balance
    trades = Import_Acct_Balance(controller, trades, local_settings)    

    #Fill up table with all info
    trades = Fill_Table_With_Info(trades, m1m2_prices, m1usd_prices, m2usd_prices)


    #############################################
    #Make the data to plot from start holding time
    org_mrk1bal = trades.tail(n=1)["Mrk1Balance"].iloc[0]
    org_mrk2bal = trades.tail(n=1)["Mrk2Balance"].iloc[0]

    trades["holding_balance"] = org_mrk1bal * trades["midspread_price"] + org_mrk2bal
    trades["traded_balance"]  = trades["Mrk1Balance"] * trades["midspread_price"] + trades["Mrk2Balance"]

    
    #Plot the price
    #ax = plt.gca()
    f, (ax, ax2, ax3) = plt.subplots(3, sharex=True)
    trades_sell = trades.loc[ trades["type"] == "sell"]
    trades_buy  = trades.loc[ trades["type"] == "buy"]

    #Plot traded
    trades_sell.plot(ax=ax, x="time", y="traded_balance", x_compat=True,style="rx",label="sells") 
    trades_buy.plot(ax=ax, x="time", y="traded_balance", x_compat=True,style="go",mfc='None',label="buys") 
    trades.plot(ax=ax, x="time", y="traded_balance", x_compat=True,color="m", label="Traded") 

    #Plots holding
    trades.plot(ax=ax, x="time", y="holding_balance",x_compat=True,color="b",label="Holding")
    trades.plot(ax=ax, x="time", y="holding_balance",x_compat=True,style="bx",label="")

    #Plot price
    trades.plot(ax=ax2, x="time", y="midspread_price",x_compat=True,style="bx",label='') 
    trades.plot(ax=ax2, x="time", y="midspread_price",color="b",label="Midspread")

    #Volume Plots
    #bar chart doesn't work with datetime pandas
    trades_sell.plot(ax=ax3, x="time", y="vol",style="rx",x_compat=True,label="sells") #kind="bar" ,x_compat=True
    trades_buy.plot( ax=ax3, x="time", y="vol",style="go",mfc='None',label="buys",x_compat=True) #kind="bar" ,x_compat=True
    #rects1 = ax2.bar(trades_sell["unixtime"], trades_sell["vol"], color='r', width=1, label='Sell')

    #Make Pretty
    ax.xaxis_date()
    ax.legend()
    ax.set_ylabel("Balance in XBT")
    ax.set_xlabel("time")

    ax2.legend()
    ax2.set_ylabel("Price")
    ax2.set_xlabel("time")

    ax3.legend()
    ax3.set_ylabel("Volume in ETH")
    
    plt.tight_layout()
    plt.show()

    #Find the first time 
    latest_time = trades.head(n=1)["time"].iloc[0]
    start_time = latest_time - pd.Timedelta(days=1)
    #start_time = start_time.apply(pd.to_datetime)
    
    #Make new dataframe for those trades
    trades_plot = trades.loc[ trades["time"] > start_time ]

    print(trades_plot)
    trades_plot["time"] = trades_plot["time"].apply(pd.to_datetime)

    plt.clf()
    plt.cla()
    plt.close()
    #plt.gcf().clear()
    f, (ax4, ax5, ax6) = plt.subplots(3, sharex=True)

    #Plotting just trades works
    trades_plot.plot(ax=ax4, x="time", y="traded_balance", x_compat=True,color="m", label="Traded") 

    ax4.xaxis_date()
    ax4.legend()
    ax4.set_ylabel("Balance in XBT")
    ax4.set_xlabel("time")

    plt.tight_layout()
    plt.show()

    #########
    #Plot traded price for buys and sells on this plot
    #Plot_Price(trades, price_tag = "midspread_price", title="XETHXXBT")

    day_step = 1
    num_plots = 5
    
    for dayi in range(1, 1 + num_plots*day_step, day_step):

        #Find the first time 
        latest_time = trades.head(n=1)["time"].iloc[0]
        start_time = latest_time - pd.Timedelta(days=dayi)

        #Make new dataframe for those trades
        trades_plot = trades.loc[ trades["time"] > start_time ]

        org_mrk1bal = trades_plot.tail(n=1)["Mrk1Balance"].iloc[0]
        org_mrk2bal = trades_plot.tail(n=1)["Mrk2Balance"].iloc[0]
        
        trades_plot["holding_balance"] = org_mrk1bal * trades_plot["midspread_price"] + org_mrk2bal
        trades_plot["traded_balance"]  = trades_plot["Mrk1Balance"] * trades_plot["midspread_price"] + trades_plot["Mrk2Balance"]
        
        #Plot the price
        #ax = plt.gca()
        plt.clf()
        plt.cla()
        plt.close()
        #plt.gcf().clear()
        f, (ax, ax2, ax3) = plt.subplots(3, sharex=True)
        trades_sell = trades_plot.loc[ trades_plot["type"] == "sell"]
        trades_buy  = trades_plot.loc[ trades_plot["type"] == "buy"]
        
        #Plot traded
        trades_sell.plot(ax=ax, x="time", y="traded_balance", x_compat=True,style="rx",label="sells")

        trades_buy.plot(ax=ax, x="time", y="traded_balance", x_compat=True,style="go",mfc='None',label="buys") 
        trades_plot.plot(ax=ax, x="time", y="traded_balance", x_compat=True,color="m", label="Traded") 
        
        #Plots holding
        trades_plot.plot(ax=ax, x="time", y="holding_balance",x_compat=True,color="b",label="Holding")
        trades_plot.plot(ax=ax, x="time", y="holding_balance",x_compat=True,style="bx",label="")

        #Plot price
        trades.plot(ax=ax2, x="time", y=price_tag,x_compat=True,style="rx",label='') 
        trades.plot(ax=ax2, x="time", y=price_tag,color="r",label=price_tag)

        #Volume Plots
        #bar chart doesn't work with datetime pandas
        trades_sell.plot(ax=ax3, x="time", y="vol",style="rx",x_compat=True,label="sells") #kind="bar" ,x_compat=True
        trades_buy.plot( ax=ax3, x="time", y="vol",style="go",mfc='None',label="buys",x_compat=True) #kind="bar" ,x_compat=True
        #rects1 = ax2.bar(trades_sell["unixtime"], trades_sell["vol"], color='r', width=1, label='Sell')
        
        #Make Pretty 
        ax.xaxis_date()
        ax.legend()
        ax.set_ylabel("Balance in XBT")
        ax.set_xlabel("time")
        
        ax2.legend()
        ax2.set_ylabel("Price")
        ax2.set_xlabel("time")
        
        ax3.legend()
        ax3.set_ylabel("Volume in ETH")
        
        plt.tight_layout()
        plt.show()

    #First of all plot the spot price
    ax = plt.gca()
    trades["trade-hold"] = trades["traded_balance"] - trades["holding_balance"]
    trades.plot(ax=ax, x="time", y="trade-hold", x_compat=True,color="m",label="Trade-Hold") #style="rx",

    plt.tight_layout()
    plt.show()

    #Plot the sell volume increase and buy volume increase
    ax = plt.gca()
    trades1 = trades.loc[ trades["type"] == "buy" ]
    trades1["buyvol"] = trades1["vol"] * (trades1["midspread_price"] - trades1["traded_price"])

    trades1.plot(ax=ax, x="time", y="buyvol", x_compat=True,color="m",label="Buying Vol") #style="rx",

    trades1 = trades.loc[ trades["type"] == "sell" ]
    trades1["sellvol"] = trades1["vol"] * (trades1["traded_price"] - trades1["midspread_price"] )

    trades1.plot(ax=ax, x="time", y="sellvol", x_compat=True,color="r",label="Selling Vol") #style="rx",

    plt.tight_layout()
    plt.show()


####################################
def Plot_Price(trades, price_tag, title):
    """Plot the price of trades vs time. 
                    
        Args:                                                                                            
            -trades (pandas dataframe) : contains trades history
            -prince_tag (str) : the label of the column of trades to plot.
            -title (str) : the title of the plots
        Returns:                                                                                         
            -Nothing returned.                                                                                            
     """

    
    ax = plt.gca()


    #Interpolated Estimated spot price
    #style='k--', color, kind=bar
    trades.plot(ax=ax, x="time", y=price_tag,x_compat=True,style="rx",label='') 
    trades.plot(ax=ax, x="time", y=price_tag,color="r",label=price_tag)

    ax.legend()
    ax.set_ylabel("Price")
    ax.set_xlabel("time")
    ax.set_title(title)
    
    plt.tight_layout()
    plt.show()

##########################
def Remove_Trades_Without_Market(trades, prices):
    """Remove elements of the trades table that do not have 
       any prices associated with them.  
                    
        Args:                                                                                            
            -trades (pandas dataframe) : contains trades history
            -prices (pandas dataframe) : contains price history
        Returns:                                                                                         
            -trades (pandas dataframe) : all with prices
     """

    latest_spot_time = prices["unixtime"].iloc[0]
    oldest_spot_time = prices.tail(n=1)["unixtime"].iloc[0]

    trades = trades.loc[ trades["unixtime"] < latest_spot_time ]
    trades = trades.loc[ trades["unixtime"] > oldest_spot_time ]

    return trades

#######################################
def Find_Price_At_Time(prices, unixtime):
    """Find the interpolated price between two trade times
       as the linear average. Returns np.nan if no trades within
       two hour window. 
                    
        Args:                                                                                            
            -prices (pandas dataframe) : contains price history
            -unixtime (int) : the time at which to find the price from. 
        Returns:                                                                                         
            -price (float) : the price of asset at time unixtime. 
     """

    #First get time below and above time, ordered by decreasing time
    row_above = prices.loc[ prices["unixtime"] > unixtime ].tail(n=1)
    row_below = prices.loc[ prices["unixtime"] < unixtime ].head(n=1)

    #If no above data try use lower
    if row_above.empty:
        if not row_below.empty:
            #if the time is two hours old don't use
            if row_below["unixtime"].iloc[0]   < (unixtime - 60*60*2):
                return np.nan
            else:
                return row_below["price"].iloc[0]
        else:
            return np.nan

    #If no below data try use upper
    if row_below.empty:
        if not row_above.empty:
            #if the time is two hours new then don't use
            if row_above["unixtime"].iloc[0]   > (unixtime + 60*60*2):
                return np.nan
            else:
                return row_above["price"].iloc[0]
        else:
            return np.nan


    #If the data is two hours old then don't use
    if row_above["unixtime"].iloc[0] > (unixtime + 60*60*2):
        if row_below["unixtime"].iloc[0]   < (unixtime - 60*60*2):
            return np.nan


            
    #slope = (y2-y1)/(x2-x1)
    slope = (row_above["price"].iloc[0] - row_below["price"].iloc[0]) / (row_above["unixtime"].iloc[0] - row_below["unixtime"].iloc[0])

    #interpolated price from a line
    price = slope * ( unixtime - row_below["unixtime"].iloc[0]) + row_below["price"].iloc[0]
    
    #Take the price as it would line on a line between two points
    return price
    

####################################################
def Read_In_Kraken_History_CSV(name):
    """Get All trades from csv file in Kraken History tab and 
       put in a pandas dataframe. 
                    
        Args:                                                                                            
            -name (str) : filename of the file to read from. 
        Returns:                                                                                         
            -trades (pandas dataframe) : contains trades history
     """

    #kraken get_trades_history only gives last 50 trades through their API.
    #But give all up to 2 days ago on their history
    #Try read in the file
    try:
        trades = pd.read_csv(name,header=0,index_col=0,keep_date_col=True,parse_dates=True,infer_datetime_format=True)

        #Arrange by time latest first
        trades.sort_values(by=["time"], inplace=True, ascending=False)

        #Rename price to traded price
        trades.rename(columns={"price" : "traded_price"}, inplace=True)
    except Exception:
        traceback.print_exc()
        print("Something went wrong with reading in csv file : ", filename)

        
    #Find out number of trades done in this history file
    num_trades = len(trades.index)
    print("This is number of trades we have done in file : ", num_trades)
    return trades

####################################################
def Read_Price_CSV(name):
    """Get price from file and put into a pandas dataframe
                    
        Args:                                                                                            
            -name (str) : filename of the file to read from. 
        Returns:                                                                                         
            -prices (pandas dataframe) : contains price history
     """

    #Try read in the file
    try:
        #Read in the prices
        col_names = ["time", "price"]
        prices = pd.read_csv(name, names=col_names, header=None, keep_date_col=True,parse_dates=True,infer_datetime_format=True)

        #Arrange by time latest first
        prices.sort_values(by=["time"], inplace=True, ascending=False)

        #Convert time to unix time
        to_unixtime= ["unixtime"]
        prices["unixtime"]  = prices["time"]
        prices[to_unixtime] = prices[to_unixtime].apply(pd.to_datetime)
        prices[to_unixtime] = prices[to_unixtime].astype('int64') // 10**9

        
    except Exception:
        traceback.print_exc()
        print("Something went wrong with reading in csv file : ", filename)
        raise

    #
    return prices

##########################################
def Add_In_API_Trades(controller, trades):
    """Add in the recent API Trades into the trades dataframe
                    
        Args:                                                                                            
            -controller (class) : a connection to the client server
        Returns:                                                                                         
            -trades (pandas dataframe) : contains trades history
     """

    #Get API Trades 
    trades_api, cnt = next(controller.client_cycler).get_trades_history()

    #Rename the columns to get in same format as the CVS file
    trades_api.rename(columns={"price" : "traded_price"}, inplace=True)
    trades_api.rename(columns={"time" : "unixtime"}, inplace=True)

    #Make time datetime 
    trades_api["time"] = trades_api.index
    trades_api["time"] = trades_api["time"].apply(pd.to_datetime)
    
    #Set index to be compatible with others
    trades_api.set_index("txid",inplace=True)

    #Append to trades
    trades = trades_api.append(trades,sort=False)
    
    #Arrange by time latest first
    trades.sort_values(by=["unixtime"], inplace=True, ascending=False)
    print(trades)
    
    #Remove duplicates
    trades = trades[~trades.index.duplicated(keep='first')]
    return trades



##################################
def Clean_Up_Trades_Book(settings, trades):
    """Remove the data that we do not need from dataframe
       and put the data we do need into consistent format
                    
        Args:                                                                                            
            -settings (dictionary) : dictionary of settings
            -trades (pandas dataframe) : contains trades history
        Returns:                                                                                         
            -trades (pandas dataframe) : contains trades history
     """

    #Clean up the trades orderbook
    pair = settings["Ex_Market1"] + settings["Ex_Market2"] # "XETHXXBT"
    trades = trades[ trades["pair"] == pair ]

    #Only keep these columns
    cols_to_keep = ["vol","time", "type", "traded_price"]
    trades = trades[cols_to_keep]
    
    #Add the columns to the dataframe we want
    kwargs = {}
    cols_to_create = ["midspread_price", "market_price", "Mrk1Balance", "Mrk2Balance", "Mrk1USD", "Mrk2USD"]
    for coli in cols_to_create:
        kwargs[coli] =np.nan

    #Put into trades 
    trades = trades.assign(**kwargs)

    #Convert strings to floats
    to_float = ["vol", "traded_price", "Mrk1Balance", "Mrk2Balance"]
    trades[to_float] = trades[to_float].apply(pd.to_numeric, errors='coerce')

    #Convert time to unix time
    trades["time"] = trades["time"].apply(pd.to_datetime)
    to_unixtime= ["unixtime"]
    trades["unixtime"] = trades["time"]
    trades[to_unixtime] = trades[to_unixtime].apply(pd.to_datetime)
    trades[to_unixtime] = trades[to_unixtime].astype('int64') // 10**9

    return trades


#######################
def Import_Acct_Balance(controller, trades, settings):
    """Add account balance into tradebook
                    
        Args:                                                                                            
            -controller (class) : a connection to the client server
            -trades (pandas dataframe) : contains trades history
            -settings (dictionary) : dictionary of settings
        Returns:                                                                                         
            -trades (pandas dataframe) : contains trades history
     """
    
    #Get Account balance so can backtrack to original balance
    acct_balance = next(controller.client_cycler).get_account_balance()
    print("This is the acct balance : ")
    print(acct_balance)

    #Put balances into latest time
    index = trades.index[0]
    trades.at[index, "Mrk1Balance"] = float(acct_balance["vol"].loc[settings["Ex_Market1"]])
    trades.at[index, "Mrk2Balance"] = float(acct_balance["vol"].loc[settings["Ex_Market2"]])

    return trades


#######################################
def Fill_Table_With_Info(trades, mrk1mrk2_prices, mrk1usd_prices, mrk2usd_prices):
    """Fill the dataframe will all the data that has been scrapped. 
                    
        Args:                                                                                            
            -mrk1mk2_prices (float) : The price of asset 1 in units of asset 2. 
            -mrk1usd_prices (float) : The price of asset 1 in units of usd
            -mrk2usd_prices (float) : The price of asset 2 in units of usd
            -trades (pandas dataframe) : contains trades history
        Returns:                                                                                         
            -trades (pandas dataframe) : contains trades history
     """

    #Loop over the trades
    for index in trades.index:

        #Get the row to fuck with
        row = trades.loc[index]
        #print(row)
        
        #This is the unixtime
        unixtimei = row["unixtime"]

        #Get the market prices of the various quantities
        mrk1mrk2_price = Find_Price_At_Time(mrk1mrk2_prices, unixtimei)
        mrk1usd_price  = Find_Price_At_Time(mrk1usd_prices,  unixtimei)
        mrk2usd_price  = Find_Price_At_Time(mrk2usd_prices,  unixtimei)

        #Add values to dataframe
        trades.at[index, "midspread_price"] = mrk1mrk2_price
        trades.at[index, "market_price"] = mrk1mrk2_price
        trades.at[index, "Mrk1USD"] = mrk1usd_price
        trades.at[index, "Mrk2USD"] = mrk2usd_price

        
        #And add account balance by backtracking. 
        if trades["type"].loc[index] == "sell":
            old_mrk1_vol = row["Mrk1Balance"] + row["vol"]
            old_mrk2_vol = row["Mrk2Balance"] - row["traded_price"] * row["vol"]
                
        elif trades["type"].loc[index] == "buy":            
            old_mrk1_vol = row["Mrk1Balance"] - row["vol"]
            old_mrk2_vol = row["Mrk2Balance"] + row["traded_price"] * row["vol"]
        
        #Try put in the new balances into previous row
        try:
            iloc = trades.index.get_loc(index)
            next_index = trades.index[iloc+1]
            trades.at[next_index, "Mrk1Balance"] = old_mrk1_vol
            trades.at[next_index, "Mrk2Balance"] = old_mrk2_vol
            
        except:
            print("Have not updated the balances for this row number: ", iloc+1)
            #raise

    #
    return trades

##################################
#Call the main with the input file
##################################
if __name__ == '__main__':

    #Specify input params
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", help="The key for kraken", nargs='*', default='', type=str)
    parser.add_argument("--secret", help="The secret for kraken", nargs='*', default='', type=str)
    parser.add_argument("--settings", help="Local settings file with input parameters", required=True, type=str)
    args = parser.parse_args()

    #Read local settings
    print(args.settings)
    local_settings = utl.Read_JSON_File(args.settings)

    #Initialise the Kraken
    controller = KrakenMidSpread(key=args.key,
                                 secret=args.secret,
                                 settings=local_settings,
                                 )


    #Initialise stuff for checking not sharp changes in midspread
    rpm = controller.Get_MidSpread_Price(controller.market)
    midspread_check = pd.DataFrame({"unixtime" : [ int(time.time()) ], "price" : [rpm] })
    
    #Call main after importing input params. 
    main()



