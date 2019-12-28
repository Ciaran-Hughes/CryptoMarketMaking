"""
Description: Child class that implements the Midspread Strategies
             on the Kraken Exchange. 

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
import traceback
from itertools import cycle

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

#Import the KrakenCore
from KrakenCore import KrakenCore

class KrakenMidSpread(KrakenCore):

    #############################
    #Find and post best bid number
    #############################
    def Find_And_Post_BestBid(self, rpm, Orderbook, Volume_Stack, settings, balance_ratio):
        """
        This function does most of the heavy lifting. 
        It will loop over the volume stacking and 
        compute the prices to post at, while doing the 
        checks to make sure there is no fuck ups. 
        We should always be thinking of more fuck ups. 

        Parameters
        ----------
        rpm : float
        - The reference price to apply leans to. 
        Orderbook : list
        - Contains the asks and bids orderbook 
        Volume_Stack: dict
        - Contains the volumes in units of market 
          and displacement (in units of basis points)
        settings : dict
        - Contains the settings
        balance_ratio: float
        - The ratio of balances for the two markets
        Returns
        -------
        None. Just posts the bids to Kraken
        """

        #Get the minimal volume we are trading
        min_vol = float(min(list(Volume_Stack.values())))

        #Get open orders to avoid volume stacking
        base_vol = 0.0
        open_orders = self.Get_Open_Orders("buy")

        #Loop over the different orders in stacking
        for displacement, volume in Volume_Stack.items():
            #Set the displacement based on stacking
            d = float(displacement)
            vol_float = float(volume)

            #Skew the prices based on Formulas
            bid_price = self.Apply_Bid_Lean2_Price(self.lean, self.l, d, rpm,balance_ratio,settings)
            
            #Since there will be a lot of dust around the best price
            #Use this ordering for optimal speed
            bids = self.Remove_DustVol_From_BidOrderBook(self.dust,volume,Orderbook)

            #Find next bid smaller than ours
            bids = self.Remove_BestBids_From_OrderBook(bids, bid_price)

            #if any bids, put one above
            if bids.empty:
                bid_price = bid_price
            else:
                #Need to sort the the orders correctly
                our_best_bid = bids["price"].sort_values(ascending=False).iloc[0]
                bid_price = float(our_best_bid) + self.min_price

            #Cancel the open orders between the necessary volumes
            self.Cancel_Open_Orders(open_orders, base_vol, vol_float)

            #Now post our bid at this price
            time_multi_factor = float(volume)/min_vol
            self.PostBid(bid_price,volume,settings,time_multi_factor)
        
    #############################
    #Make Bid. 
    #############################
    def PostBid(self,bid_price,vol2trade,settings,time_fac):

        """
        This function posts the actual bid after checking if it's in the book
        
        Parameters
        ----------
        bid_price : float
        - The price to post the bid
        vol2trade : str
        - The volume to trade
        settings : dict
        - The dictionary of settings, used to determine the expiry time
        time_fac : float
        - The multiplication factor to keep larger orders in the book
        Returns
        -------
        Nothing, just posts the bid
        """
        #If the Bid is not in the book, move it up to best bid
        bid_price = self.Check_Bid_In_Book(bid_price)
        bid_price = round(bid_price,self.min_price_digit)

        #Decide then to start can cancel orders
        starttm, expiretm = self.Get_StartExpire_Time_For_Trades(
            settings["starttmAdd"],
            settings["expiretmAdd"],
            time_fac)

        #Post bid
        print(self.market + " bid price is " + str(bid_price) + " with volume " + vol2trade)
        #If the post works, great, if not continue
        try:
            order_buy = next(self.client_cycler).add_standard_order(pair=self.market,
                                                                    type="buy",
                                                                    ordertype="limit",
                                                                    volume=vol2trade,
                                                                    price=bid_price,
                                                                    validate=False,
                                                                    #starttm=starttm,
                                                                    expiretm=expiretm,
                                                                    oflags="post")
            
            print("This is the bid order: ")
            print(order_buy)

        except Exception:
            traceback.print_exc()
            return
            
        
    #############################
    #Make Ask 
    #############################
    def PostAsk(self,ask_price, vol2trade,settings,time_fac):
        """
        This function posts the actual ask after checking if it's in the book
        
        Parameters
        ----------
        ask_price : float
        - The price to post the ask
        vol2trade : str
        - The volume to trade
        settings : dict
        - The dictionary of settings, used to determine the expiry time
        time_fac : float
        - The multiplication factor to keep larger orders in the book
        Returns
        -------
        Nothing, just posts the ask
        """
        
        #Make sure we are in the right side of the book
        #If not move it to best ask + min_price
        ask_price = self.Check_Ask_In_Book(ask_price)        
        ask_price = round(ask_price,self.min_price_digit)

        #Decide then to start can cancel orders
        starttm, expiretm = self.Get_StartExpire_Time_For_Trades(
            settings["starttmAdd"],
            settings["expiretmAdd"],
            time_fac)

        #Place the Order
        print(self.market + " ask price is " + str(ask_price) + " with volume " + vol2trade )
        #If post doesn't work then start return
        try:
            order_sell = next(self.client_cycler).add_standard_order(pair=self.market,
                                                                     type="sell",
                                                                     ordertype="limit",
                                                                     volume=vol2trade,
                                                                     price=ask_price,
                                                                     validate=False,
                                                                     #starttm=starttm,
                                                                     expiretm=expiretm,
                                                                     oflags="post")
            print("This is the ask order: ")
            print(order_sell)
        except Exception:
            traceback.print_exc()
            return


    #############################
    #Find and post best ask number
    #############################
    def Find_And_Post_BestAsk(self,rpm, Orderbook, Volume_Stack,settings,balance_ratio):
        """
        This function does most of the heavy lifting. 
        It will loop over the volume stacking and 
        compute the prices to post at, while doing the 
        checks to make sure there is no fuck ups. 
        We should always be thinking of more fuck ups. 

        Parameters
        ----------
        rpm : float
        - The reference price to apply leans to. 
        Orderbook : list
        - Contains the asks and bids orderbook 
        Volume_Stack: dict
        - Contains the volumes in units of market 
          and displacement (in units of basis points)
        settings : dict
        - Contains the settings
        balance_ratio : float
        - The ratio of balances of accounts interested in.
        Returns
        -------
        None. Just posts the asks to Kraken
        """

        #Get the minimal volume we are trading
        min_vol = float(min(list(Volume_Stack.values())))

        #Get open orders to avoid volume stacking
        base_vol = 0.0
        open_orders = self.Get_Open_Orders("sell")
        
        #Loop over the different orders in stacking
        for displacement, volume in Volume_Stack.items():
            d = float(displacement)
            vol_float = float(volume)

            #Skew the prices based on Formulas
            ask_price = self.Apply_Ask_Lean2_Price(self.lean,self.l,d,rpm,balance_ratio,settings)
            
            #Since there will be a lot of dust around the best price
            #Use this ordering for optimal speed
            asks = self.Remove_DustVol_From_AskOrderBook(self.dust,volume,Orderbook)

            #Find next bid smaller than ours
            asks = self.Remove_BestAsks_From_OrderBook(asks, ask_price)

            #if any bids, put one above
            if asks.empty:
                ask_price = ask_price
            else:
                #Need to sort the orders correctly
                our_best_ask = asks["price"].sort_values().iloc[0]
                ask_price = float(our_best_ask) - self.min_price

                
            #Cancel the open orders between the necessary volumes
            self.Cancel_Open_Orders(open_orders, base_vol, vol_float)
                        
            #Now post our bid at this price
            time_multi_factor = float(volume)/min_vol
            self.PostAsk(ask_price,volume,settings,time_multi_factor)



    #############################
    #Find and post best ask number
    #############################
    def Get_Open_Orders(self, ordertype):

        """
        Return the open orders of type ordertype        

        Parameters
        ----------
        ordertype : str
        - sell or buy based on what you want
        Returns
        -------
        open_orders : pandas dataframe
        - all open orders
        """
        #Get open orders to cancel last stacking
        try:
            
            #Get open orders to know what to cancel to avoid accidental stacking
            open_orders = next(self.client_cycler).get_open_orders()
            
            #Since each key is restricted to one market pair
            #We only need to restrict to ordertype and not pair/limit
            open_orders = open_orders.loc[ open_orders["descr_type"] == ordertype ] 
            
            #Convert the volumes to numbers
            cols = 'vol'
            open_orders[cols] = open_orders[cols].apply(pd.to_numeric, errors='coerce')
            
        except Exception:
            print("Was not able to get asks open orders")
            traceback.print_exc()
            open_orders = {}

        return open_orders
        

    #############################
    #Find and post best ask number
    #############################
    def Cancel_Open_Orders(self, open_orders, base, vol):
        """
        Cancel open orders with a volume between base and vol

        Parameters
        ----------
        open_orders : pandas dataframe
        - the open orders
        base : float
        - The base volume from which to neglect above
        vol : float
        - The max volume from which to ngelect below
        Returns
        -------
        base_vol : float
        - the new base value for the next iteration
        """
        
                                      
        #Remove the orders we don't want to avoid accidental double stacking
        try:
            #Get all open orders between current volume and base volume
            orders_to_close = open_orders.loc[ base < open_orders["vol"] ]  # <= vol_float
            #The number 1e-7 is just to put a min increment over vol_float
            orders_to_close = orders_to_close.loc[ orders_to_close["vol"] <= vol + 0.000000001 ]
            
            #and cancel them
            txnids = orders_to_close.index
            for txn in txnids:
                try:
                    cancel_order = next(self.client_cycler).cancel_open_order(txn)
                except Exception:
                    traceback.print_exc()
                
            #Reset the base to the current volume for next cycle of loop
            base_vol = vol
            
        except Exception:
            traceback.print_exc()
            base_vol = 0.0

        return base_vol
