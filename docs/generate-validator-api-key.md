# **Generate Validator API Key for ReadyAI Conversation Server**

Validators are required to generate an API key to access the ReadyAI Conversation Server. This server serves full conversations, which validators tag to establish ground truth and divide into windows used to query miners as part of our novel *fractal data mining* process. To generate your key, please follow the below instructions. 

## Retrieve your hotkey and coldkey information

To retrieve your coldkey name, you can run `btcli wallet list` via the command line, which will display your bittensor coldkeys and hotkeys. Find the coldkey and hotkey associated with your validator, and retrieve the local names of these keys.

## Run the generation script

Once you have your key names, you can run the local script. Run this against mainnet with the below command from the top-level directory of this repository:

```
python scripts/get_validator_api_key.py
```

To run this on testnet, run the below command: 
```
python scripts/get_validator_api_key.py test
```

You will then be prompted to enter the subnet netuid, which is 33 by default (enter 138 for testnet), your wallet path, and your coldkey and hotkey names, both of which you retrieved in the previous step.

Once you enter the above information, the script will check your wallet information against the subnet metagraph to confirm you are a validator, check that you possess the minimum validator stake, and then sign a transaction from your hotkey. If the signature is successful, you will see the following print: 

```
COLDKEY <coldkey address> is registered on subnet: COLDKEY:<coldkey address>, IS VALIDATOR:True, TOTAL STAKE:<validator stake>
Signing message...
Signature is valid
Signed. Get API key...
Got API key, writing to file...


ReadyAI key successfully generated and stored in file: readyai_api_data.json
    Place this json file in your validator execution directory.
```

You should now be able to successfully retrieve conversations from the ReadyAI Conversation Server. For troubleshooting, please see the section below. 

## Troubleshooting

Below is a list of errors and how to troubleshoot each. 

```
Coldkey <coldkey address> not registered on subnet. Aborting. 
# This indicates that the coldkey was not found on the specified subnet's metagraph. Please confirm that you have the correct coldkey for your validator.

Validator <uid> unstaked: <coldkey address> validator:<vpermit> stake: <stake amount> 
# This indicates that your coldkey was found to not have a hotkey with the minimum required stake to retrieve a validator API Key

Not Validator <uid> : <coldkey address> stake: <stake amount> 
# This indicates that the coldkey does not have a vpermit on any of its affiliated hotkeys. Please confirm that you have the correct coldkey for your validator

Coldkey <uid> is not a validator : <is_validator>. Aborting. 
# This indicates that the coldkey does not have a vpermit on any of its affiliated hotkeys. Please confirm that you have the correct coldkey for your validator

Total state of <stake amount> is less than minimum stake of <minimum stake>. Aborting. 
# This indicates that your coldkey was found to not have a hotkey with the minimum required stake to retrieve a validator API Key

scalecodec is not installed. Aborting. 
# This indicates that you do not have the required package to decode your SS58 coldkey address. Please confirm that you have bittensor installed. If you're using a virtual environment, please confirm you have it activated with Bittensor installed.

Error posting to <url>: <response status code> - <response text> 
# This error occurs when there is a problem posting to the Conversation Server. Likely there is a problem with your connectivity and/or network environment. Please check your internet connection, and for further assistance please reach out to the discord.

Error getting message: <Error Text> 
# This is a network error that may occur when trying to receive the encryption message from the Conversation server. Please check your internet connection, and for further assistance please reach out to the discord.

Keygen Error: <Error Text> 
# This is an encryption error. Please confirm that you have bittensor installed, and if you're using a virtual environment, confirm that you have it activated. For further assistance please reach out to the discord.

Error loading coldkey: <Error Text> 
# This error may occur if your coldkey is not stored locally of if there is an error with your path or wallet name. Please confirm that you have the correct coldkey information for your validator, and that the coldkey is stored locally.

Signature is not valid 
# This is an encryption error. Please confirm that you have bittensor installed, and if you're using a virtual environment, confirm that you have it activated. Please also confirm that you have the correct coldkey information for your validator, and that the coldkey is stored locally. For further assistance please reach out to the discord.

```

For further questions or technical assistance, please reach out on the SN33 discord channel [here](https://discord.gg/bittensor)
