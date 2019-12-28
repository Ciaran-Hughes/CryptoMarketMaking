"""
Description: Kraken only allow users access to 24hrs worth of past transactions.
             This KrakenRecordBot.py script will set up a connection to 
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

#Import the modules needed for Kracken API
import krakenex
from pykrakenapi import KrakenAPI

#Import the Kraken Recorder
sys.path.append("../master_code/")
#from filename import class
import KrakenRecorder as kr

#################################### Main program #######################
def main(local_settings, controller):
    """Run the bot to always record the data from the client server,
       even if the bot encounters some problem (most likely from connection
       issues). 
                    
        Args:                                                                                            
            -local_settings (dictionary): A list of settings to initialise 
                                          the recording, eg., which market 
                                          to record
            -controller (class KrakenCall()): The class which handles the connection to the 
                                         client servers. 

        Returns:                                                                                         
            -Nothing returned.                                                                                            
     """

    #Do this so code always runs
    try:
        while True:
            kr.RecordBot(local_settings, controller)

    except Exception as e:
        print("Error : {0}".format(e))
        print("Recording Bot in"+str(os.getcwd())+" has broken.")
        print("########################################")
        print("Restarting After Error")
        print("########################################")
        main(local_settings, controller)


##################################
if __name__ == '__main__':
    """
    The main file will run the code with the proper keyword args
    #1: the local settings input file
    """

    #Make sure we have one command line arguments for the Kracken API connection
    if len(sys.argv[1:]) != 1:
        print("Need to specify one input to command line argument relevant for API calls")
        print("This is local settings file")
        sys.exit()

    #Read local settings
    local_settings = kr.Read_Local_Settings(sys.argv[1])
    
    #Initialise the Kraken
    controller = kr.KrakenCall(market=local_settings["pair"])
    
    #If we have the input params, run main. Otherwise exit
    try:
        main(local_settings, controller)
    except: 
        print("Error in opening main")
        print("in"+str(os.getcwd()))

