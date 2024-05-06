#!/bin/bash

# check if a parameter is passed
if [ -z "$1" ]; then
  echo
  echo -e "\033[31mError: Need to pass the name of your wallet and hotkey. For example:"
  echo -e "bash start_miner_api.sh rp rp-hot\033[0m"
  echo
  exit 1
fi

python3 -m neurons.miner --netuid 1 --subtensor.chain_endpoint ws://api.conversation.org:9946 --wallet.name $1 --wallet.hotkey $2 --logging.debug
