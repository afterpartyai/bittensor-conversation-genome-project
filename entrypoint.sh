#!/bin/sh
set -e

echo "Type: $TYPE, Network: $NETWORK"

# Determine what module to execute based on TYPE
if [ "$TYPE" = "validator" ]; then
    SCRIPT="neurons.validator"
elif [ "$TYPE" = "miner" ]; then
    SCRIPT="neurons.miner"
else
    echo "Unknown type: $TYPE"
    exit 1
fi

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

# Construct arguments
ARGS="--netuid $NETUID --wallet.name $COLDKEY_NAME --wallet.hotkey $HOTKEY_NAME --axon.port $PORT --subtensor.network $SUBTENSOR_NETWORK --subtensor.chain_endpoint $CHAIN_ENDPOINT"

# Add debug mode if enabled
[ -n "$DEBUG_MODE" ] && ARGS="$ARGS --logging.debug"

# Execute the command
exec python3 -m $SCRIPT $ARGS