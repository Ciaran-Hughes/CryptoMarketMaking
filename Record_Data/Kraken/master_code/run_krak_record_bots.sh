#!/bin/bash

#Description: This bash script will start running all the recording bots on the Kraken exchange for the markets declared in the file. 

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


echo "We are recording a total of ${#markets[@]} markets"
for market in "${markets[@]}"
do
    cd ../
    if [ ! -d "PDNS-${market}" ]
    then
	echo "Making the directory for ${market}"
	mkdir "PDNS-${market}"
    fi
    cd "PDNS-${market}"

    echo "Coping files to ${market} directory"
    cp ../master_code/KrakenRecordBot.py .
    cp ../master_code/PDNS-LocalSettings.json .
    cp ../master_code/hd5_reader.py .
    sed -ie "s/market/${market}/g" PDNS-LocalSettings.json

    echo "Running tmux session"
    tmux new -d -s ${market}
    tmux send-keys -t ${market} "python3 KrakenRecordBot.py PDNS-LocalSettings.json" Enter
    cd ../master_code
    echo "Finishing ${market}"
    sleep 5
    echo ""
done

