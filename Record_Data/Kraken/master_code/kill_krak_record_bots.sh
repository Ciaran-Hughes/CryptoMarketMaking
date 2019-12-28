#!/bin/bash

#Description: This bash script will kill all the recording bots on the Kraken exchange for the markets declared in the file. Note that the recording bots have been setup to always run even if an error is found. 

#Author: Ciaran Hughes  <http://mailto:iamciaran2@gmail.com>
#Author: Rian   Hughes  <http://mailto:rian.hughes@physics.ox.ac.uk>
#Date  : August 2018
#Version: 1.0.1
#Maintainers: Authors
#Status: Production

#Make list of markets
markets=("XETHXXBT" 
    "XXBTZEUR"
    "XXBTZUSD"
    "DASHXBT"
    "BCHXBT"
    "XXMRXXBT"
    "XETCXXBT"
    "XLTCXXBT"
    "USDTZUSD"
    "XXLMXXBT"
    "XZECXXBT"
    "DASHUSD"
    "DASHEUR"
    "EOSXBT"
    "EOSUSD"
    "EOSEUR"
    "EOSETH"
    "BCHUSD"
    "BCHEUR"
    "XETCZUSD"
    "XETCZEUR"
    "XETCXETH"
    "XETHZUSD"
    "XETHZEUR"
    "XLTCZUSD"
    "XLTCZEUR"
    "XXLMZUSD"
    "XXLMZEUR"
    "XXMRZUSD"
    "XXMRZEUR"
    "XZECZUSD"
    "XZECZEUR")

for market in "${markets[@]}"
do
    echo "Killing tmux session: ${market}"
    tmux kill-session -t ${market}
done

