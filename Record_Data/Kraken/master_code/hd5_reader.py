"""
Description: A template script that reads hdf5 data formats and prints 
             the information. This is to be used in order to visually
             inspect the recorder transactions. 
             Assumes that RecordBot.py has been run to record past 
             transactions

Author: Ciaran Hughes  <http://mailto:iamciaran2@gmail.com>
Author: Rian   Hughes  <http://mailto:rian.hughes@physics.ox.ac.uk>
Date  : August 2018
Version: 1.0.1
Maintainers: Authors
Status: Production

"""

#Import relevant modules
from __future__ import division

#Import the modules needed for data IO
import pandas as pd
import json

#################################### Main program #######################
def main():

    filename = "../ETHXBT/2018/8/30/PDNS-Kracken_XETHXXBT.h5"
    past_trades = pd.read_hdf(filename)

    print("These are the past trades from : ", filename)
    print(past_trades)

    print("The Data is being recorded in from Kraken as a pandas Dataframe ")
    print("This allows for easy timeseries manipulation")
    print("The files are being stored in pandas hdf format")
    print("Hieracherical Data Format")
    print("Use the pandas HDStore functions to read")
    print("Or select subset of data at read or print time")
    print("pd.read_hdf() should be all that is needed with optional params")

##################################
if __name__ == '__main__':
    """
    """
    try:
        main()
    except: 
        print("Main Failed")
        raise


