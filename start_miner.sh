export RAND_PORT=$((RANDOM%201+8913)) 
echo Starting miner on port $RAND_PORT
python3 -m neurons.miner  --axon.port $RAND_PORT --blacklist.force_validator_permit --netuid 1 --subtensor.chain_endpoint ws://127.0.0.1:9946 --wallet.name miner --wallet.hotkey default --logging.debug
