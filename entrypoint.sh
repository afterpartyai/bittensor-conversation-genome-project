#!/bin/sh
set -e

echo "Type: $TYPE, Network: $NETWORK, Coldkey: $COLDKEY_NAME, Hotkey: $HOTKEY_NAME, Port: $PORT, IP: $IP"

# Set network parameters
case "$NETWORK" in
  finney)
    NETUID=33
    SUBTENSOR_NETWORK="finney"
    CHAIN_ENDPOINT="wss://entrypoint-finney.opentensor.ai:443"
    ;;
  test)
    NETUID=138
    SUBTENSOR_NETWORK="test"
    CHAIN_ENDPOINT="wss://entrypoint-test.opentensor.ai:443"
    ;;
  *)
    echo "Unknown network: $NETWORK"
    exit 1
    ;;
esac

# Default arguments
ARGS="--netuid $NETUID --wallet.name $COLDKEY_NAME --wallet.hotkey $HOTKEY_NAME --subtensor.network $SUBTENSOR_NETWORK"

# Determine the command to execute
case "$TYPE" in
  validator)
    CMD="python3 -m neurons.validator"
    ;;
  miner)
    CMD="python3 -m neurons.miner"
    ;;
  *)
    echo "Unknown type: $TYPE"
    exit 1
    ;;
esac

# Append extra arguments for miner/validator
if [ "$TYPE" = "validator" ] || [ "$TYPE" = "miner" ]; then
    ARGS="$ARGS --axon.port $PORT --axon.external_port $PORT --axon.ip $IP --axon.external_ip $IP --subtensor.chain_endpoint $CHAIN_ENDPOINT"

    [ -n "$DEBUG_MODE" ] && ARGS="$ARGS --logging.debug"

    [ "$NETWORK" = "test"] && ARGS="$ARGS --blacklist.allow_non_registered"
fi

# Print the final command for debugging
echo "Executing: $CMD $ARGS"

# Execute the command
exec $CMD $ARGS
