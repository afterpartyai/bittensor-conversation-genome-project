export RAND_PORT=$((RANDOM%201+9000))
echo Starting validator on port $RAND_PORT

python3 -m neurons.validator --netuid 1 --subtensor.chain_endpoint ws://127.0.0.1:9946 --wallet.name validator --wallet.hotkey default --logging.debug
