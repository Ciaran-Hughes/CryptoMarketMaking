"""
Description: This KrakenCore class is the main parent class of all bots 
             that are going to trade on various exchanges, either to make 
             profits or provide liquidity in market making. Child classes
             will implement specific strategies for trading (VWAP,TWAP, etc).

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
from collections import OrderedDict
from itertools import cycle
import traceback

#Import the modules needed for Kracken API
import krakenex
from pykrakenapi import KrakenAPI
import Utils as utl

#Import the modules needed for data IO
import pandas as pd
import json
import numpy as np

#Custome made modules
sys.path.append("../../../..")
#Need to point the TraderBot to the FileBot
sys.path.append("../../../../FileBot/")
import BotFile

######################################
class KrakenCore():
    def __init__(self,
                 key=[''],
                 secret=[''],
                 sftppassword='',
                 settings=None):

        """
        Constructor of the Kraken Core Class
        
        This sets up the connection to Kraken and sets the global
        variables. 
        
        Parameters
        ----------
        key : list of str, optional
        -The keys to a kraken account
        secret : list of str, optional
        -The secrets to a kraken account
        sftppassword : str, optional
        -The password to the sftpserver
        settings : dict, optional
        - A dictionary of the settings to be used
        Returns
        -------
        Class 
        - A kraken core class
        """
        
        #Check if market specified in settings file and 
        #Figure out what market we are interested in
        if not "Ex_Market1" in settings.keys():
            print("Need a Kraken Exchange market specified in the settings file")
            print("Specify Ex_Market1 keyword in settings file")
            raise
        if not "Ex_Market2" in settings.keys():
            print("Need a Kraken Excahnge market 2 specified in the settings file")
            print("Specify Ex_Market2 keyword in settings file")
            raise
    
        else:
            market=settings["Ex_Market1"] + settings["Ex_Market2"]

        #
        #Do Trivial checks 
        if market=="":
            raise NameError("No market pair defined. Add pair=xxx to the Controller initialization")
        if key==['']:
            print("No Kraken Key defined. No key=xxx given to the Controller initialization")
        if secret==['']:
            print("No Kraken secret defined. No secret=xxx given to the Controller initialization")


        #Make the connections once for better practice
        #without storing keys
        #Try make all connection to the Kracken API
        try:

            print("Using Keys from input")
            print("*****MAKE SURE KEYS/SECRETS IN RIGHT ORDER")
            #Loop over all keys/secrets
            self.clients = []
            for keyj, secretj in zip(key,secret):

                #Make the connection
                api_j = krakenex.API(key=keyj, secret=secretj)
                #Use the kraken wapper for better functionality
                self.clients.append( KrakenAPI(api_j) )

            #Make a way to cycle through the keys
            self.client_cycler = cycle(self.clients)            
        except:
            traceback.print_exc()
            print("Couldn't make a connection to the Kraken API")
            print("exit")
            raise
        
        #Setup FileBot if there is any
        self.Setup_FileBot(settings, sftppassword)

        #Save for later
        self.market = market
        self.min_price = settings["min_increment"] #This is not bp
        self.bp = 0.0001 #This is bp
        self.acct_mrkt1 = self.Kraken_Lookup_Acct_Market(settings["Ex_Market1"])
        self.acct_mrkt2 = self.Kraken_Lookup_Acct_Market(settings["Ex_Market2"])

        #Find the number of significant digits so we can round 
        #the price later
        digits = format(self.min_price, ".16f")
        #Seperate based on dot
        digits = digits.partition(".")[2]
        self.min_price_digit = len(digits) - len(digits.lstrip("0")) + 1

        #Setup stuff        
        if "dust" in settings.keys():
            self.dust = settings["dust"]

        if "volume" in settings.keys():
            self.tot_vol = settings["volume"]

        if "odepth" in settings.keys():
            self.odepth = settings["odepth"]
        #

    ##########################################
    def Setup_Volume_Stacking(self, settings, kraken_api=None):
        """
        Sets up the Volume Stacking of prices
        
        Parameters
        ----------
        settings : dict
        - A dictionary of required inputs
        kraken_api : class, optional
        - A client to the kraken server to be used to convert
          the bitcoin volumes into different market volumes
        
        Returns
        -------
        Volume_Stack : dict
        -The keys are the displacement in bp and values are the volumes
        """
        
        Volume_Stack = OrderedDict()
        
        #Check if specified in settings file to use Stale Volume Stacking
        if not "VolumeStacking" in settings.keys():
            #Are we going to Dynamically stack his orders. 
            self.Dynamical_Stack = False
            print("No Volume Stacking parameter in settings file, defaulting to not using it. Using displacement form sftp.")
            #Put all volume in one place
            Volume_Stack[str(self.d)] = self.tot_vol

        elif settings["VolumeStacking"]=="None":
            self.Dynamical_Stack = False
            #Put all volume in one place
            print("No volume stacking. Using displacement from sftp.")
            Volume_Stack[str(self.d)] = self.tot_vol

            #TODO: elif == sftp then read from sftp server.  self.volume_stack_file = 'sftp'
        else:
            self.Dynamical_Stack = True

            #Read in a put into ordered dictionary
            temp_stack = utl.Read_JSON_File(settings["VolumeStacking"])

            print("Reading in local Stale Volume Stacking values from")
            print(settings["VolumeStacking"])

            #Can use this later for reloading
            self.volume_stack_file = settings["VolumeStacking"]
            
            #Remove the comments and put in scaling factors
            temp_stack.pop("_comment_")
            vol_distortion = float(temp_stack.pop("volume_distortion"))
            bp_distortion = float(temp_stack.pop("bp_distortion"))

            #Check that total volume from file then check total volume in
            #settings file.
            vol_file = 0.0
            for voli in temp_stack.values():
                vol_file += float(voli)
            #
            if abs(float(self.tot_vol) - vol_file) > 10e-3:
                print("Total volume in Stacking file : ", settings["VolumeStacking"])
                print("Does not equal volume in Settings file")
                print("Make them equal")
                print("From Settings : ", self.tot_vol)
                print("From Volume Stacking : ", vol_file)
                print("Difference : ", abs(float(self.tot_vol) - vol_file))
                sys.exit(1)


            #Now scale by the appropiate factors to ensure in the right market
            #As all stacking is given in XBT units
            if kraken_api==None:
                print("Need to give an api for volume stacking to compute conversations")
                print("from XBT to market")
                            
            #Need to covert volume from XBT units to other markets
            if not settings["Ex_Market1"] in ["XXBT", "XBT"]:

                mrkt, pos = self.Kraken_Lookup_XBT_Market(settings["Ex_Market1"])
                
                midspread = kraken_api.Get_MidSpread_Price(mrkt)

                if pos == 1:
                    conversation = midspread
                elif pos == 2:
                    conversation = 1.0 / midspread
                else:
                    print("XBT market position labelled wrong in loopup table")
                    raise
                
            elif settings["Ex_Market1"] in ["XXBT", "XBT"]:
                conversation = 1.0
                
            else:
                print("Need a market. Not specified correctly for volume stacking")
                raise
                
            
            #Now read the rest in as orders. 
            for bp, voli in temp_stack.items():
                new_bp = float(bp) * bp_distortion
                new_vol= float(voli) * vol_distortion * conversation
                Volume_Stack[str(new_bp)] = str(new_vol)

                
        #Return out of function
        print("This is volume stack : ")
        print(Volume_Stack)
        return Volume_Stack

    ##########################################
    def Setup_FileBot(self, settings, sftppass):
        """
        Setup the connection to the filebot, either static or not.

        Parameters
        ----------
        settings : dict
        - a dictionary of settings to use
        sftppass : str
        - password for the sftpserver
        
        Returns
        -------
        Puts everything into self        
        """
        
        #Check if specified in settings file to use FileBot or not
        if not "FileBot" in settings.keys():
            print("No FileBot parameter in settings file, defaulting to not reading in FileBot")
            return
        else:
            FileBot = settings["FileBot"]

        #Figure out if we are using a stale file bot
        #or need to read from the SFTP Server
        #
        if FileBot == "None":
            print("Specified to not use Filebot")
            return

        #We need to know the markets for the file bots
        if not "market1" in settings.keys():
            print("You have specified to read with a Filebot")
            print("Therefore you need a market1 to determine values from")
            raise
        if not "market2" in settings.keys():
            print("You have specified to read with a Filebot")
            print("Therefore you need a market1 to determine values from")
            raise 
       
        self.mrkt1 = settings["market1"]
        self.mrkt2 = settings["market2"]

        if FileBot=="sftp":
            #Try make a connection to the Botfile
            try:
                #If using the sftpserver check that we have the values needed for a connection
                if not "sftphost" in settings.keys():
                    print("Havent specified sftphost in settings file but want to connect")
                    raise
                if not "sftpusername" in settings.keys():
                    print("Havent specified sftpusename in settings file but want to connect")
                    raise

                #Initialise Values
                sftphost=settings["sftphost"]
                sftpusername=settings["sftpusername"]
                
                #Do trivial check
                if sftphost=="":
                    raise ("No SFTP host defined. Add sftphost=xxx to the Controller initialization")
                if sftpusername=="":
                    raise ("No SFTP user name defined. Add sftpusername=xxx to the Controller initialization")
                if sftppass=="":
                    raise ("No SFTP password defined. Add sftppassword=xxx to the Controller initialization")

                #Start the connection
                print("Connecting to sftp server")
                self.botfileclient = BotFile.BotFile(host=sftphost, username=sftpusername, password=sftppass)
                self.bfc = self.botfileclient.getBotFile2()["data"]
                self.Set_Botfile_Params()
                self.last_read_time = int(time.time())
            except Exception as e:
                print("Error : {0}".format(e))
                print("Couldn't make a connection to the BotFile")
                print("exit")
                sys.exit(1)
        #If asked for a stale/static filebot, then read in stale/staic values
        else:
            #Put the input values from file into stalefilebot
            StaleFileBot = utl.Read_JSON_File(FileBot)
            print("Reading in local StaleFileBot values")

            self.bfc = StaleFileBot
            self.Set_Botfile_Params()
            self.last_read_time = int(time.time())



                
    #############################
    def Reload_Params(self,reload_time, Volume_Stack, settings, sftppass):
        """
        A function to reload all of the global paramters
        
        Parameters
        ----------
        reload_time : int
        - how often to read in the new settings
        Volume_Stack : dictionary
        - The volume stacking to update
        settings : dict
        - Dictionary of the options
        sftpass : 
        - The password for the sftpserver
        Returns
        -------
        reloads the new settings into self
        TODO: Reload Volume Settings and return.         
        """
        _reload = int(time.time()) - self.last_read_time - reload_time
        if _reload >0.0:
            #Need old displacement if using the static. 
            old_displacement = self.d
        
            self.Setup_FileBot(settings, sftppass)

            #Need to change this to just call Setp_Volume_Stack instead
    
            #If there is a static volume stacking we need to update the
            #displacment read from sftp
            if not self.Dynamical_Stack:
                Volume_Stack[str(self.d)] = self.Volume_Stack.pop(old_displacement)
            #If dynamical volume_stacking then update the volume_stack
            else:
                Volume_Stack = Volume_Stack
            #
            self.last_read_time = int(time.time())

        return Volume_Stack
        
    #############################
    #Get the public trade data
    def Get_Public_Trades(self,since):
        """
        Gets the publically traded Data off Kraken 
        
        Parameters
        ----------
        since : int
        - how far back to retrieve the trade data
        -Currently broke on Kraken and gets all data
                
        Returns
        -------
        public_trades : list
        -This returns a 2-array: [trades, current-time]
        """
        #How much data to pull from public trade history
        #since is broken in Kraken API.
        if since == "None":
            since = None

        #Make most recent data on top
        ascending = False
        public_trades = next(self.client_cycler).get_recent_trades(self.market,since,ascending)
        return public_trades    

    #############################
    def Set_Botfile_Params(self):
        
        """
        Re-initialise the values from the botfile
        
        Parameters
        ----------
        
        Returns
        -------
        Updates parameters into self
        """
        
        mrkt1 = self.mrkt1
        mrkt2 = self.mrkt2
        #Get the parameters from the BotFile        
        self.lean = self.bfc[mrkt1]["lean"][mrkt2]
        self.l = self.bfc[mrkt1]["l"][mrkt2]
        self.d = self.bfc[mrkt2]["displacement"]

        #Print them
        print("lean = " + str(self.lean))
        print("L = " + str(self.l))


    #############################
    def Apply_Ask_Lean2_Price(self,lean,l,d,rpm,balance_ratio,settings):

        """
        Applies the displacement and leans to the reference price (rpm)
        
        Parameters
        ----------
        lean : float
        - the lean to use to decide what formulas to use
        l : float
        - the numerical value to alter the rpm in terms of basis points (percentage)
        d : float
        - the displacement to alter the rpm in terms of basis points (percentage)
        rpm : float
        - the numerical value of the reference price which we will alter
        balance_ratio : float
        - Our balance ratio in units of the second market
        settings: dict
        - A dictionary of all settings
        Returns
        -------
        ask_price : float
        - The ask_price we should post at
        """
        
        #Compute the Ask Local lean
        local_lean = self.Get_Ask_Local_Lean(balance_ratio,settings)
        
        #Skew the prices based on Formulas
        if lean >=0.0:
            print("Lean Positive or Zero")
            ask_price = rpm * (1.0 + d + l + local_lean)
        elif lean < 0.0:
            print("Lean Negative")
            ask_price = rpm * (1.0 + d + local_lean)
        else:
            print("Lean is not a number")
            raise


        return ask_price

        
    #############################
    def Get_StartExpire_Time_For_Trades(self,starttmAdd,expiretmAdd,time_fac=1.0):

        """
        Set the expiry time for orders 
        
        Parameters
        ----------
        starttmAdd : int
        - The number of seconds to post the trade after current server time
        expiretmAdd : int
        - The number of seconds to expire the trade after current server time
        time_fac : float, optional
        - the factor to multiply the expiry time by
        Returns
        -------
        starttm : int
        - the unixtime to start trade
        expiretm : int
        - the unixtime to end trade

        Improvements
        ----------
        Make this an array for volume stacking
        """
        
        #When to start and expire the trades relative to server time
        #Kraken functionality broken. Need to do ourselves 
        #and if in <n> then it's absolute unixtime
        server_time = next(self.client_cycler).get_server_time()[1]
        starttm = server_time + starttmAdd
        expiretm= server_time + expiretmAdd*time_fac

        print("Relative to Kraken, our trades start (seconds) at +", starttmAdd)
        print("And end "+str(expiretmAdd*time_fac)+" seconds later")

        return starttm, expiretm

    #############################
    #Get the public trade data. depth=100 on kraken default
    def Get_OrderBook(self, mrkt, depth=100):

        """
        A function to get the orderbook from Kraken
        
        Parameters
        ----------
        mrkt : str
        - The market to get the orderbook for
        depth : int, optional
        - How many orders in the orderbook to get
        
        Returns
        -------
        orderbook : list
        - The orderbook where the [0] element is the asks and [1] is the bids
        """
        orderbook = next(self.client_cycler).get_order_book(mrkt,depth)
        return orderbook
        
    #############################
    #Get Best Ask and Bid from orderbook
    def Get_Best_AskBid(self, orderbook):

        """
        Get the best ask and bid from the orderbook
        Parameters
        ----------
        orderbook : list 
        - The orderbook 

        Returns
        -------
        best_ask : float
        - The best ask in the orderbook
        best_bid : float
        - The best bid in the orderbook
        """
        best_ask = float(orderbook[0]['price'].sort_values(ascending=True ).iloc[0])
        best_bid = float(orderbook[1]['price'].sort_values(ascending=False).iloc[0])

        return best_ask, best_bid
        
    #############################
    def Check_Bid_In_Book(self,bid_price):

        """
        Check if the price we are posting our bid is higher than the 
        best bid in the orderbook. If it is, then make our bid one basis
        point above than the orderbook best bid. If it's not, return our best bid

        Parameters
        ----------
        bid_price : float
        - What we suspect the best bid is
        
        Returns
        -------
        bid_price : float
        - What our bid price should be
        """
        #Get the best bid
        best_ask, best_bid = self.Get_Best_AskBid(
            self.Get_OrderBook(depth=1,mrkt=self.market))

        #If our price is higher than the best bid then
        #Make it one basis point higher
        if bid_price > best_bid:            
            bid_price = best_bid + self.min_price
            print("In the wrong side of book, adjusting price to 1bp above best bid")
        return bid_price
            
    #############################
    #Check that the ask is in the right side of book
    #And we aren't selling for too little
    #############################
    def Check_Ask_In_Book(self,ask_price):

        """
        Check if the price we are posting our ask is lower than the 
        best ask in the orderbook. If it is, then make our ask one basis
        point lower than the orderbook best ask. If it's not, return our best ask. 

        Parameters
        ----------
       ask_price : float
        - What we suspect the ask bid is
        
        Returns
        -------
        ask_price : float
        - What our ask price should be
        """
        #Get the best ask
        best_ask, best_bid = self.Get_Best_AskBid(
            self.Get_OrderBook(depth=1,mrkt=self.market))

        #If our price is less than the best ask then
        #Make it one basis point lower
        if ask_price < best_ask:
            ask_price = best_ask - self.min_price
            print("In the wrong side of book, adjusting price to 1bp below best ask")
        return ask_price
        
    #############################
    def Get_OHLC(self,candlestick_size, number_of_sticks):
        """
        Retrieve the open-high-low-close candle data from the exchange

        Parameters
        ----------
        candlestick_size : int
        -Time in minutes to average the trade data to produce candlestick.
        -Allowed values found on https://github.com/dominiktraxl/pykrakenapi/blob/master/pykrakenapi/pykrakenapi.py
        number_of_sticks : int
        - how many candlesticks do you want
        
        Returns
        -------
        ohlc_data : list
        - [0] element is the ohlc data in pandas dataframe format. [1] is the read time        
        """
        server_time_ohlc = next(self.client_cycler).get_server_time()[1]
        #The number 60.0 is in there because Kraken define candlestick_size
        #in terms of minutes but server time in terms in seconds. 
        ohlc_data = next(self.client_cycler).get_ohlc_data(self.market, candlestick_size, server_time_ohlc-60.0*candlestick_size*number_of_sticks )
        return ohlc_data


    #############################
    #Clean order Book based on dust volume
    #############################
    def Remove_DustVol_From_BidOrderBook(self, dust, volume, orderbook):
        """
        The orderbook contains all orders of all volumes. 
        However we want to remove those orders which have smaller volume than
        we care about. We call those orders dust. This function removes dust 
        from the bids. 
        
        Parameters
        ----------
        volume : str
        - The total volume of the order we want to post
        dust : str 
        - The fraction of the volume we want to consider dust, e.g., 0.1
        orderbook : list
        - The orderbook

        Returns
        -------
        bids : pandas dataframe
        - The bids without the dust
        """
        #Get all bids that have volumes greater than specified dust value
        bids = orderbook[1]

        #Need to make the orderbook numbers
        cols = ['price', 'volume']
        bids[cols] = bids[cols].apply(pd.to_numeric, errors='coerce')

        #tot_vol is str, dust is float. 
        return bids.loc[ bids["volume"] > float(dust)*float(volume) ]
                     
    #############################
    #Clean order Book based on dust volume
    #############################
    def Remove_DustVol_From_AskOrderBook(self, dust, volume, orderbook):
        """
        The orderbook contains all orders of all volumes. 
        However we want to remove those orders which have smaller volume than
        we care about. We call those orders dust. This function removes dust 
        from the asks. 
        
        Parameters
        ----------
        volume : str
        - The total volume of the order we want to post
        dust : str 
        - The fraction of the volume we want to consider dust, e.g., 0.1
        orderbook : list
        - The orderbook

        Returns
        -------
        asks : pandas dataframe
        - The asks without the dust
        """        

        #Get all asks that have volumes greater than specified dust value
        asks = orderbook[0]

        #Need to make the orderbook numbers
        cols = ['price', 'volume']
        asks[cols] = asks[cols].apply(pd.to_numeric, errors='coerce')

        return asks.loc[ asks["volume"] > float(dust)*float(volume) ]

        
    #############################
    def Remove_BestAsks_From_OrderBook(self,asks,price):
        """
        We want to find the order in the orderbook which has the closest price ours. 
        So we make the best post as possible. Remove all asks smaller than price. 

        Parameters
        ----------
        asks : pandas dataframe
        - All the orderbook asks
        price : float
        - The price to remove all asks below.

        Returns
        -------
        asks: pandas dataframe
        - The asks above price
        """
        #Pandas wants str
        return asks[ asks["price"] > price ]

    #############################
    #Clean Bid order Book based on price
    #############################
    def Remove_BestBids_From_OrderBook(self,bids,price):
        """
        We want to find the order in the orderbook which has the closest price ours. 
        So we make the best post as possible. Remove all bids larger than price. 

        Parameters
        ----------
        bids : pandas dataframe
        - All the orderbook asks
        price : float
        - The price to remove all asks below.

        Returns
        -------
        bids: pandas dataframe
        - The bids below price
        """
        #Pandas wants str
        return bids[ bids["price"] < price ]
        
        

    #############################
    #Look up table for kraken Markets if xbt
    #not specified for one of the markets.
    #Needed for at least volume stacking where
    #need xbt as reference market price
    #############################
    def Kraken_Lookup_XBT_Market(self, mrkt):
        """
        For the volume stack the volumes are in bitcoin units. 
        In order to convert to the units of the market we are on
        we need the exchange rate. This is a lookup table for how
        to find the market which needs to be converted from bitcoin. 

        Parameters
        ----------
        mrkt : str
        - The market with which we need to find the exchange rate
          relative to bitcoin

        Returns
        -------
        (pair,position): tuple
        - The pair is what Kraken calls the market relative to bitoin
        - The position is where bitcoin occurs in pair. E.g., if it's firstr
          then the market is already in bitcoin units, in contrast to second. 
        """
        
        #The tag for the xbt market and
        #what position xbt is in
        Kraken_Ref_XBT = {}
        Kraken_Ref_XBT["DASH"] = ("DASHXBT",2)
        Kraken_Ref_XBT["USD"]  = ("XXBTZUSD",1)
        Kraken_Ref_XBT["EUR"]  = ("XXBTZEUR",1)
        Kraken_Ref_XBT["ZUSD"] = ("XXBTZUSD",1)
        Kraken_Ref_XBT["ZEUR"] = ("XXBTZEUR",1)
        Kraken_Ref_XBT["EOS"]  = ("EOSXBT",2)
        Kraken_Ref_XBT["ETH"]  = ("XETHXXBT",2)
        Kraken_Ref_XBT["XETH"] = ("XETHXXBT",2)
        Kraken_Ref_XBT["BCH"]  = ("BCHXBT",2)
        Kraken_Ref_XBT["XETC"] = ("XETCXXBT",2)
        Kraken_Ref_XBT["XLTC"] = ("XLTCXXBT",2)
        Kraken_Ref_XBT["XXLM"] = ("XXLMXXBT",2)
        Kraken_Ref_XBT["XXMR"] = ("XXMRXXBT",2)
        Kraken_Ref_XBT["XZEC"] = ("XZECXXBT",2)

        if not mrkt in Kraken_Ref_XBT.keys():
            print("The market you are asking for isn't referenced in lookup table")
            print("you need to add it")
            raise
        else:
            return Kraken_Ref_XBT[mrkt]

    #############################
    def Kraken_Lookup_Acct_Market(self, mrkt):
        """
        For the account balance calls, the name of the account balance pair
        can be different from the name of the market pair. Thanks Kraken.
        This function returns the account pair names.

        Parameters
        ----------
        mrkt : str
        - The market with which we need to find the account name for

        Returns
        -------
        acct_mrkt : str
        - The account market name to be used in the get account balance API call
        """

        acct_mrkt = mrkt         
        if mrkt == "XBT":
            acct_mrkt = "XXBT"

        return acct_mrkt

    #############################
    def Get_MidSpread_Price(self, mrkt):
        """
        Compute the midspreak price for the mrkt

        Parameters
        ----------
        mrkt : str
        - The market to compute the midspread price

        Returns
        -------
        midspread : float
        - The midspread price for mrkt
        """
        
        #Get the best bid and ask from order book
        best_ask, best_bid = self.Get_Best_AskBid(
            self.Get_OrderBook(depth=1,mrkt=self.market))


        #Compute midspread
        midspread = 0.5*(best_bid + best_ask)
        print("This is the midspread price: ", midspread)
        return midspread


    #############################
    def Get_Bid_Local_Lean(self,R,settings):
        """
        Apply a lean to price based on local balances
        We may want to be defensive or aggressive. 
        Currently implements exponential defensivness

        Parameters
        ----------
        R: float
        - The ratio of balances to know to be agressive or defensive
        settings: dict, 
        - Dictionary of the local settings file

        Returns
        -------
        loc_lean : float
        - The local lean
        """
                
        #If less market1 than market2 assets
        #and posting big, then we may want to
        #be more defensive on letting our product go. 
        if R > 1.0:
            #Compute the local lean in terms of 
            loc_lean = np.exp(R - 1.0) - 1.0
            loc_lean *= settings["local_defense"] * self.bp

        #If we have less of market1 we may want
        #to be more defensive on the sell
        elif R < 1.0:
            #Not implemented yet - needs to be negative to push up
            loc_lean = 0.0
            
        else:
            print("Not doing a local lean because R isn't set right. 0<R<infinity :  ", R)

        #Return the new local lean price
        return loc_lean


    #############################
    def Get_Ask_Local_Lean(self,R,settings):

        """
        Apply a lean to price based on local balances
        We may want to be defensive or aggressive. 
        Currently implements exponential defensivness

        Parameters
        ----------
        R: float
        - The ratio of balances to know to be agressive or defensive
        settings: dict, 
        - Dictionary of the local settings file

        Returns
        -------
        loc_lean : float
        - The local lean
        """

        #If more market1 than market2 assets
        #and posting ask, then we may want to
        #be more agreesive
        if R > 1.0:
            #Needs to be negative to push downx
            loc_lean = 0.0
        
        #If we have less of market1 we may want
        #to be more defensive on the sell
        elif R < 1.0:
            #Compute the local lean in terms of 
            loc_lean = np.exp(1.0/R - 1.0) - 1.0
            loc_lean *= settings["local_defense"] * self.bp
            
        else:
            print("Not doing a local lean because R isn't set right. 0<R<infinity :  ", R)

        #Return the new local lean price
        return loc_lean

    #############################
    def Get_Acct_Balances(self, price, settings):

        """
        Get the account balances of the account for the markets

        Parameters
        ----------
        settings: dict, 
        - Dictionary of the local settings file
        price : 
        - The price to compute one market volume in termsof the other

        Returns
        -------
        balance_ratio : float
        - The ratio of balances computed in units of the second market
        """

        #Get acct balance for checks
        acct_balance = next(self.client_cycler).get_account_balance()
        
        #Figure out account volume 
        mrkt1_vol = float(acct_balance["vol"].loc[self.acct_mrkt1])
        mrkt2_vol = float(acct_balance["vol"].loc[self.acct_mrkt2])
        
        #Find out the ratio of balances
        #The requires a price conversion in terms of the first market
        #So that volumes in term of the second market
        balance_ratio = (mrkt1_vol * price) / mrkt2_vol

        return balance_ratio


    ####################################
    def Check_No_Large_Price_Change(self,current_price, price_change, recordbook):
        """
        This function records data over a day timeframe and checks if the current price
        lies outside the mean value of the recorded data up to the price_change precentage. 

        Parameters
        ----------
        current_price : float
        - The current price of the market
        price_change : float
        - The maximum allowed deviation from the mean market price
        recordbook : pandas dataframe
        - a record of all prices up to a day timeframe

        Returns
        -------
        recordbook : pandas dataframe
        - The updated recordbook
        """


        #unixtime of one day
        oneday = 60*60*24

        #current time
        current_time = int(time.time())

        #Remove entries older than a day
        recordbook = recordbook[recordbook["unixtime"] > (current_time - oneday) ]

        #Compute the mean price of the recorded data
        mean_price = recordbook["price"].mean()
        
        #Add a price into the data
        datum = pd.DataFrame({ "unixtime" : [current_time],
                               "price" : [current_price]
        })
        recordbook = recordbook.append(datum)


        #Check if current price is too large or too small
        if abs(current_price) > abs(mean_price * (1.0 + price_change)):
            print("Current price is outside the specific price range allowed")
            print("current_price", current_price)
            print("mean_price", mean_price)
            print("price_change", price_change)
            raise
        elif abs(current_price) < abs(mean_price * (1.0 - price_change)):
            print("Current price is outside the specific price range allowed")
            print("current_price", current_price)
            print("mean_price", mean_price)
            print("price_change", price_change)
            raise
        
        else:
            return recordbook

        
