"""
Description: This module contains utility functions to be used throughout
             code base. 

Author: Ciaran Hughes  <http://mailto:iamciaran2@gmail.com>
Author: Rian   Hughes  <http://mailto:rian.hughes@physics.ox.ac.uk>
Date  : August 2018
Version: 1.0.1
Maintainers: Authors
Status: Production

"""
#Import the modules needed for data IO
import json

#########################################
#Read in local settings. 
#########################################
def Read_JSON_File(input_file):
    """Read the local settings froma json file. 
                    
        Args:                                                                                            
            -input_file (str): The path to the json file
    
        Returns:                                                                                         
            -json_file (dictionary) : The local settings from input_file                                                                  
    """
    
    #Try to open and read the json input file
    try:
        with open(input_file, 'r') as stream:
            print("Reading from : ", input_file)
            json_file = stream.read()
            json_file = json.loads(json_file)
            
    except FileNotFoundError:
        print("Could not find input file : ", input_file)
        raise
    except:
        print("Could not parse input file : ", input_file)
        raise
    
    return json_file
