#!/bin/sh
set -e

echo "Type: $TYPE, Network: $NETWORK"

# Sets the keys to read-only for non-owner users, allowing Docker access, then runs the entrypoint script.
[ -f "/home/appuser/.bittensor/wallets/$COLDKEY_NAME/coldkeypub.txt" ] && chmod 644 "/home/appuser/.bittensor/wallets/$COLDKEY_NAME/coldkeypub.txt"
[ -f "/home/appuser/.bittensor/wallets/$COLDKEY_NAME/hotkeys/$HOTKEY_NAME" ] && chmod 644 "/home/appuser/.bittensor/wallets/$COLDKEY_NAME/hotkeys/$HOTKEY_NAME"

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
ARGS="--netuid $NETUID --wallet.name $COLDKEY_NAME --wallet.hotkey $HOTKEY_NAME"

# Determine the command to execute
case "$TYPE" in
  validator)
    CMD="python3 -m neurons.validator"
    ;;
  miner)
    CMD="python3 -m neurons.miner"
    ;;
  register)
    CMD="btcli s register"
    ;;
  *)
    echo "Unknown type: $TYPE"
    exit 1
    ;;
esac

# Append extra arguments for miner/validator
if [ "$TYPE" = "validator" ] || [ "$TYPE" = "miner" ]; then
    ARGS="$ARGS --axon.port $PORT --axon.external_port $PORT --axon.ip $IP --axon.external_ip $IP \
    --subtensor.network $SUBTENSOR_NETWORK --subtensor.chain_endpoint $CHAIN_ENDPOINT"
fi

# Print the final command for debugging
echo "Executing: $CMD $ARGS"

# Execute the command
exec $CMD $ARGS
