#!/bin/sh

echo "Type: $TYPE, Network: $NETWORK, Coldkey: $COLDKEY_NAME, Hotkey: $HOTKEY_NAME, Port: $PORT, IP: $IP"

start_services() {
  if [ "$RUNPOD" = "true" ] && [ -n "$SSH_PUBLIC_KEY" ]; then
    echo "Setting up SSH key-based access for root..."

    # Ensure SSH config allows key-based login
    mkdir -p /root/.ssh
    echo "$SSH_PUBLIC_KEY" > /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chown -R root:root /root/.ssh

    # Configure SSH to allow key-based login and disable password login
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

    echo "Starting SSH..."
    /usr/sbin/sshd &

    echo "SSH started with key-based authentication"
  fi
}

prepare_command() {
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

  case "$TYPE" in
    validator)
      CMD="python3 -m neurons.validator"
      ;;
    miner)
      CMD="python3 -m neurons.miner"
      ;;
    api)
      echo "Only starting the API"
      ;;
    *)
      echo "Unknown type: $TYPE"
      exit 1
      ;;
  esac

  if [ "$TYPE" = "validator" ] || [ "$TYPE" = "miner" ]; then
    # Make sure the Axon is served on the public IP of the node
    # 0.0.0.0 or nothing means the .env was not updated so we do it here
    if [ "$IP" = "0.0.0.0" ] || [ -z "$IP" ]; then
      IP=$(curl -s ifconfig.me)
      echo "Using fecthed IP to serve axon: $IP"
      export IP
    fi

    # If you run on Runpod, the port is mapped to a random port and therefore need to be set accordingly
    # The keys are also kept in a persistent volume at /workspace/wallets so it needs to be passed to the launch command
    if [ "$RUNPOD" = "true" ]; then
      PORT=$(echo $RUNPOD_TCP_PORT_70033)
      echo "Using port from Runpod: $PORT"
      export PORT

      ARGS="$ARGS --wallet.path /workspace/wallets"
    fi

    ARGS="$ARGS --axon.port $PORT --axon.external_port $PORT --axon.ip $IP --axon.external_ip $IP --subtensor.chain_endpoint $CHAIN_ENDPOINT"
    [ -n "$DEBUG_MODE" ] && ARGS="$ARGS --logging.debug"
  fi
}

start_api() {
  if [ "$TYPE" = "api" ] || { [ "$START_LOCAL_CGP_API" = "true" ] && [ "$TYPE" != "miner" ]; }; then
    echo "Starting local API on port ${LOCAL_CGP_API_PORT}..."
    cd /web || { echo "Failed to change to /web directory"; exit 1; }
    uvicorn app:app --host 0.0.0.0 --port "$LOCAL_CGP_API_PORT" &
    cd / || { echo "Failed to return to root directory"; exit 1; }
    echo "Local API started."
  fi
}

run_main_loop() {
  if [ "$TYPE" = "validator" ] || [ "$TYPE" = "miner" ]; then
    while true; do
      echo "[$(date)] Running command: $CMD $ARGS"
      $CMD $ARGS
      EXIT_CODE=$?
      echo "[$(date)] Command exited with code $EXIT_CODE. Retrying in 10 seconds..."
      sleep 10
    done
  fi
}

start_services
prepare_command
start_api
run_main_loop

# Failsafe
echo "Main loop exited unexpectedly. Keeping container alive..."
tail -f /dev/null