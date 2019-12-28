"""
Description: This code is the controller of all the other pieces. 
             It is the actual code you run to provide liquidity 
             with a midspread strategy. 

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

#Import the modules needed for Kracken API
import krakenex
from pykrakenapi import KrakenAPI

#Import the modules needed for data IO
import pandas as pd
import json

#Custome made modules
sys.path.append("../../../../..")
#Need to point the TraderBot to the FileBot
sys.path.append("../../../../../FileBot/")
import BotFile
#Need to point the KrackenVWAP files
sys.path.append("../../../master_code/")
#from filename import class
from KrakenMidSpread import KrakenMidSpread
import Utils as utl

#################################### Main program #######################
def main(Volume_Stack,midspread_check):
    """Run the code to post bids and asks with a midspread strategy.        

        Args:                                                                                            
            -Volume_Stack (dictionary) : How to stack the volumes of different posts
            -midspread_check (float) : The mean midspread price to avoid manipulations 
                                       when there are large changes in price
        Returns:                                                                                         
            -Nothing returned.                                                                                            
     """

    #Initialise variables outside loop
    temp_reload_counter = 0
    
    try:
        while True: 
            #
            #It's all about speed. Get best price last
            #
            #Reload the Variables
            Volume_Stack = controller.Reload_Params(local_settings["reload_time"], Volume_Stack,local_settings,args.sftppass)

            #Get Orderbook first so we can stack orders.
            #Getting order right is less important than price.
            #So get price last
            Orderbook = controller.Get_OrderBook(depth=controller.odepth,
                                                 mrkt=controller.market)

            #Get the midspread price
            rpm = controller.Get_MidSpread_Price(controller.market)

            #Check there has been no large Price changes over the last 24hrs
            midspread_check = controller.Check_No_Large_Price_Change(rpm, local_settings["price_change"], midspread_check)

            #Get Account Balance
            balance_ratio = controller.Get_Acct_Balances(rpm, local_settings)

            #Make the posts
            temp_reload_counter = Make_ShallowDeep_Posts(rpm, Orderbook, Volume_Stack, local_settings, balance_ratio, temp_reload_counter)
                
    except Exception:
        traceback.print_exc()
        print("Kraken Bot in"+str(os.getcwd())+" has broken.")
        print("########################################")
        print("Restarting After Error")
        print("########################################")
        main(Volume_Stack,midspread_check)

        
#############################
def Make_ShallowDeep_Posts(rpm, Orderbook, Volume_Stack, local_settings,balance_ratio, cntr):
    """Make the bids/asks which are shallow in the tradebook and deep in the tradebook. 

        Args:
            -rpm (float) : The price of the asset from the midspead stategy
            -Orderbook (pandas dataframe) : The book of all current trades used to predict 
                                            the best price to buy/sell. 
            -Volume_Stack (dictionary) : How to stack the volumes of different posts
            -local_settings (dictionary) : A list of the local settings.
            -balance_ratio (float) : How much do you want to buy vs sell of an asset. 
            -cntr (class)  : The KrakenCoreMidspread class which connects to the clients servers.
        Returns:                                                                                         
            -Reload_counter (int) : a counter used to identify when to update the settings of the controller. 
     """

    #Reload the shallow orders first
    #Compute Price and Post
    if  cntr < local_settings["deep_reload_counter"]:
        #This is how far down in stacking we want to go
        shallow_depth = local_settings["shallow_depth"]
        
        #Make the shallow stack
        shallow_volume_stack = {key: Volume_Stack[key] for key in list(Volume_Stack)[:shallow_depth]} 
        
        #Do shallow posting
        controller.Find_And_Post_BestAsk(rpm, Orderbook, shallow_volume_stack, local_settings,balance_ratio)
        print()
        controller.Find_And_Post_BestBid(rpm, Orderbook, shallow_volume_stack, local_settings,balance_ratio)
        
        #Increase the counter for next time
        reload_counter = cntr + 1
    else:
        
        #Do Shallow + Deep Posting
        controller.Find_And_Post_BestAsk(rpm, Orderbook, Volume_Stack, local_settings,balance_ratio)
        print()
        controller.Find_And_Post_BestBid(rpm, Orderbook, Volume_Stack, local_settings,balance_ratio)
        
        #Re initialise
        reload_counter = 0                

    return reload_counter


#############################
if __name__ == '__main__':
    """Args: Specified Below
       Returns:                                                                                         
            -Nothing returned.                                                                                            
     """

    #Specify input params
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", help="The key for kraken", nargs='*', default='', type=str)
    parser.add_argument("--secret", help="The secret for kraken", nargs='*', default='', type=str)
    parser.add_argument("--sftppass", help="The password for the sftpserver", default='', type=str)
    parser.add_argument("--settings", help="Local settings file with input parameters", required=True, type=str)
    args = parser.parse_args()

    #Read local settings
    print(args.settings)
    local_settings = utl.Read_JSON_File(args.settings)

    #Initialise the Kraken
    controller = KrakenMidSpread(key=args.key,
                                 secret=args.secret,
                                 sftppassword=args.sftppass,
                                 settings=local_settings)

    #Compute the initial volume stacking
    Volume_Stack = controller.Setup_Volume_Stacking(local_settings, controller)

    #Initialise stuff for checking not sharp changes in midspread
    rpm = controller.Get_MidSpread_Price(controller.market)
    midspread_check = pd.DataFrame({"unixtime" : [ int(time.time()) ], "price" : [rpm] })
    
    #If we have the input params, run main. Otherwise exit
    try:
        #Call main after importing input params. 
        main(Volume_Stack,midspread_check)
    except: 
        print("Main Failed")
        raise

