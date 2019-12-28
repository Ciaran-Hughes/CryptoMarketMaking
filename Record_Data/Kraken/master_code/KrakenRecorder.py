"""
Description: Kraken only allow users access to 24hrs worth of past transactions.
             This KrakenRecorder.py script will set up a connection to 
             the Kraken API client on their servers and then record and accumulate
             all past transaction history for however long this bot is run. 
             This data scraping yields more training time series data 
             and thus more accurate market trading predictions. 
             Saved in a hdf5 format using pandas dataframe. 
             Consistency of data format and tests of accuracy are also performed. 

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

#Import the modules needed for Kracken API
import krakenex
from pykrakenapi import KrakenAPI

#Import the modules needed for data IO
import pandas as pd
import json

#################################### Main program #######################
def RecordBot(local_settings, controller):
    """ This function is the driver which sets up the StoreManager class,    
        which will then continue to collect the latest data, find those 
        not already recorded, append the new data, wait and then repeat. 
        This function will call itself if an exception/error is raised 
        so to never stop recording. Therefore it is necessary to run 
        remotely in a tmux or screen enviroment so it can be killed. 
                    
        Args:                                                                                            
            -local_settings (dictionary): A list of settings to initialise 
                                          the recording, eg., which market 
                                          to record
            -controller (class KrakenCall()): The class which handles the connection to the 
                                         client servers. 

        Returns:                                                                                         
            -Nothing returned.                                                                                            
        """

    #What is the key of the hd5 file
    datatag = local_settings["pair"]
    

    #Wrap call in a try-except so to continuously record data. 
    try:
        while True: 
            
            #Get the current trades from online API
            online_trades, unique_online_tdates, online_ttimes = Get_Current_trades(local_settings["since"],
                                                                                    controller)
            
            #Loop over all distinct dates in the online trade book in pandas format.
            for year, month, day in unique_online_tdates:
                
                #Get all trade data for a specific date in the past
                oneday_online_trades = online_trades[ (online_ttimes.year == year ) &  
                                                      (online_ttimes.month== month) &  
                                                      (online_ttimes.day  == day  ) ]  
                                                     

                oneday_directory = "./"+str(year)+"/"+str(month)+"/"+str(day)+"/"
                filename = "PDNS-Kracken_"+controller.market+".h5"
                
                #make idays store manager
                oneday_file_manager = StoreManager(datatag,oneday_directory,filename)

                #Find which data is different between our file
                #and online records (which is needed to add to file)
                oneday_file_manager.Get_New_Data(oneday_online_trades)
                
                #Add any new data to the file
                oneday_file_manager.Add_Data_To_File()
                
                #Close the store
                oneday_file_manager.store.close()


            #Close while loop
            #Sleep till next time
            print("Sleeping for (secs) : ", str(local_settings["sleep"]))
            print("#"*20)
            time.sleep(local_settings["sleep"])
            
            print("########################################")
            print("Starting New Read")
            print("########################################")
            
    except Exception as e:
        print("Error : {0}".format(e))
        print("Recording Bot in"+str(os.getcwd())+" has broken.")
        print("########################################")
        print("Restarting After Error")
        print("########################################")
        RecordBot(local_settings, controller)

        
#################################
class StoreManager():
    """ The class that manages the IO of the data from the client server and 
        also appending new information to a file. 
        Checks consistency and accuracy of data. 

                    
        Args:                                                                                            
            -datatag (str)   : Which market to save the data for
            -directory (str) : which directory to save the file
            -filename (str)  : the name of the save file

        Returns:                                                                                         
            -StoreManager() class
        """
    def __init__(self,
                 datatag=None,
                 directory=None,
                 filename=None):
    
                 
        #Need this for writing and reading later
        self.datatag = datatag
        self.directory = directory 
        self.filename = filename
        
        #Check if data exists
        self.Check_Existence()
    

    #################
    ##Check for Data existence in file
    #################
    def Check_Existence(self):
    
        #Check if the folder exists
        #If not make it
        if os.path.isdir(self.directory):
            pass
        else:
            print("Making Directory for writing : ", self.directory)
            try:
                os.makedirs(self.directory)
            except Exception as e:
                print("Error : {0}".format(e))
                print("Couldn't make directory")
                raise

            
        #Check if the file exists
        #Important to know for first write or not
        if os.path.isfile(self.directory+self.filename):
            self.data_exists = True
        else:
            self.data_exists = False
        

        #Open file ourselves to reduce number of opens and closes
        try:
            self.store = pd.HDFStore(self.directory+self.filename, mode="a")
        except Exception as e:
            print("Error : {0}".format(e))
            print("Couldn't open store")
            raise

        if self.datatag not in self.store:
            self.data_exists = False


    #################
    ##Get the data which is different between the
    ##file and the online API.
    ##Needed to see if there is any data which we want
    ##to add to file
    #################
    def Get_New_Data(self,oneday_online_trades):

        #If data does not exist, then return all the trades
        if not self.data_exists:
            self.new_online_trades = oneday_online_trades
            print ("new_online_trades : ", self.new_online_trades)
            
            self.num_new = len(self.new_online_trades.index)
            print("There are "+str(self.num_new)+" new trades to add to file")
            
            if not self.num_new>0:
                print("We do not have a positive number of rows even though new data")
                sys.exit(1)

            return 

        #If data does exist, need to find the new trades compared to file
        #
        #Read the top line of previous file.
        #last_row = pd.read_hdf(store,  )
        nrows = self.store.get_storer(self.datatag).nrows
        last_file_row = self.store.select(key=self.datatag,
                                          start=nrows-1,
                                          stop =nrows)
        
        print("#"*15)
        print("This is the last row of the file : ", self.directory+self.filename)
        print("Last_file_row : ", last_file_row)
    
        #Get latest file time
        latest_file_time = last_file_row.index[0]
        lft = latest_file_time
        print("Latest filetime : ", lft)
        
        
        #Make the dataframe to append: 
        self.new_online_trades = oneday_online_trades[oneday_online_trades.index > lft ]
        print ("new_online_trades : ", self.new_online_trades)
        
        self.num_new = len(self.new_online_trades.index)
        print("There are "+str(self.num_new)+" new trades to add to file")


    #################################
    # Add data to the end of the file
    #################################
    def Add_Data_To_File(self):


        #Specify the minimum data size for the different columns
        #need to do this as first order sets all format sizes for the future
        #Need to do this as there can be a big order that goes through
        #and change the format size
        min_itemsize={ "price"    : 15,
                       "volume"   : 15,
                       "buy_sell" : 4,
                       "market_limit" : 6
        }

        
        #Add partial data to end of file if Data Exists.
        if self.data_exists:
            if self.num_new>0:
                print("Adding New Data to File : ", self.directory+self.filename)
                self.store.append(key=self.datatag,
                                  value=self.new_online_trades,
                                  format='table',
                                  append=True,
                                  min_itemsize=min_itemsize
                )
            else:
                print("Do not need to add any new trade data to file : ", self.directory+self.filename)

        #If data doesn't exist then add all of it to the file
        else:
            if self.num_new>0:
                print("Adding new data to the file : ", self.directory+self.filename)
                print("With rows : ", self.num_new)
                
                self.store.append(key=self.datatag,
                                  value=self.new_online_trades,
                                  format='table',
                                  append=False,
                                  min_itemsize=min_itemsize                 
                )
                
            else: #if num_new<=0
                print("No rows to add even though we have no existing data")
                sys.exit(1)


##############################
class KrakenCall():
    """ The class manages the handshake and connection to the clients
        servers, as well as sets up the API. 
                    
        Args:                                                                                            
            -market (str)   : Which market to save the data for

        Returns:                                                                                         
            -KrakenCall() class
        """


    def __init__(self,market=None):

        #Make sure the intialised values are set for the Connections
        if market==None:
            raise NameError("No market pair defined. Add pair=xxx to the Controller initialization")


        #Make the connections once for better practice
        #without storing keys
        #Try make a connection to the Kracken API
        try:
            api = krakenex.API()
            #Use the kraken wapper for better functionality
            self.client = KrakenAPI(api)
        except:
            print("Couldn't make a connection to the Kraken API")
            print("exit")
            sys.exit(1)
        
        #
        self.market = market


##################################
def Get_Current_trades(since,controller):
    """ This function gets the current trades listed on the 
        client API. 
                    
        Args:                                                                                            
            -since (int) : How long ago should we collect data for
                           unixtime. Max 24hrs prior to current time. 
            -controller (class KrakenCall()): The class which handles the connection to the 
                                         client servers. 

        Returns:                                                                                         
            -current_trades (pandas dataframe) :  Contains all the trades for the time period specified 
            -unique_online_tdates (list) : A list of tuples of the unique dates on which trades were made
                                           eg., [(year,month,day),...]
            -trade_ttimes (datetime pandas dataframe) : All dates on which trades were made

        """

    #Since is broken, doesn't work on Kraken
    if since == "None":
        since = None
        
    #Make most recent data on bottom
    ascending = True
    public_trades = controller.client.get_recent_trades(controller.market,since,ascending)
    
    #Put the info we need into variables
    current_trades = public_trades[0] #This is a dataframe
    trade_ttimes = current_trades.index #This is a datetime pandas array
    #latest_trade = current_trades.iloc[-1] #This is a dataframe
    #latest_trade_time = latest_trade.index


    #Find the unique (year,month,day) tuples
    #This is fastest way
    unique_online_tdates = []
    for datei in trade_ttimes:
        date = (datei.year,datei.month,datei.day)
        if not date in unique_online_tdates:
            unique_online_tdates.append(date)
            
    
    print("###################################")
    print("This is the current trade data")
    print("###################################")
    print("This is the times of current trades")
    print(current_trades.index)
    #print("This is the latest time")
    #print(latest_trade)
    print("###################################")

    #Return the variables
    return current_trades, unique_online_tdates, trade_ttimes
    

#########################################
def Read_Local_Settings(input_file):
    """ This function reads the input parameters from the json file 
        used to initialise everything.                     
        Args:                                                                                            
            -input_file (str) : The path/name of the json file containing
                                the local settings. 

        Returns:                                                                                         
            -local_settings (dictionary) : dictionary of local settings
        """
    
    #Try to open and read the json input file
    try:
        with open(input_file, 'r') as stream:
            print("Reading from : ", input_file)
            local_settings = stream.read()
            local_settings = json.loads(local_settings)
            
    except FileNotFoundError:
        print("Could not find input file : ", input_file)
        raise
    except:
        print("Could not parse input file : ", input_file)
        raise

    return local_settings

