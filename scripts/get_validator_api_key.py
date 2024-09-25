import bittensor as bt
import base58
from hashlib import blake2b
#from substrateinterface import Keccak

class CgpApiLib():
    def get(self):
        netuid = 1
        subnet = bt.metagraph(netuid)
        #wallet = bt.wallet( name = 'my_coldkey', hotkey = 'my_validator_hotkey' )
        otf_ss58 = '5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3'
        hotkey = otf_ss58
        #my_uid = subnet.hotkeys.index( wallet.hotkey.ss58_address )
        my_uid = subnet.hotkeys.index( otf_ss58 )
        print(f"UID for Hotkey: {hotkey} : {my_uid}")
        #mg = subnet.metagraph(netuid)
        #print("HOTKEYS", subnet.hotkeys)
        #print(f'Validator permit: {subnet.validator_permit(my_uid)}')
        if hotkey not in subnet.hotkeys:
          print(f"Hotkey {hotkey} deregistered")
        else:
          print(f"Hotkey {hotkey} is registered")
        #print(subnet.validator_permit(hotkey=hotkey))
        #print( dir(subnet))
        #print(subnet.coldkeys)
        #print(len(subnet.hotkeys), len(subnet.coldkeys), len(subnet.validator_permit), len(subnet.stake))
        print(f"HOTKEY: {subnet.hotkeys[my_uid]}, COLDKEY:{subnet.coldkeys[my_uid]}, VALIDATOR:{subnet.validator_permit[my_uid]}, STAKE:{subnet.stake[my_uid]}")
        coldkey = subnet.coldkeys[my_uid]
        import bittensor

        #wallet = bittensor.wallet(hotkey)
        #print("WALLET",wallet, dir(wallet))
        print("SUBNET",subnet, dir(subnet))
        list_object_properties(subnet)

    def list_object_properties(obj):
        properties = dir(obj)
        for prop in properties:
            try:
                value = getattr(obj, prop)
                if len(value) == 1024:
                    print(prop, value[5])
                    #print(f"{prop}: {value}")
            except Exception as e:
                pass
                #print(f"{prop}: {e}")




    def ss58_to_public_key(ss58_address: str) -> str:
        print("Converting:", ss58_address)
        """
        Convert an SS58-encoded cold key address to a public key.

        Args:
            ss58_address (str): The SS58-encoded cold key address.

        Returns:
            str: The corresponding public key.
        """
        # Decode the SS58 address
        decoded_address = base58.b58decode_check(ss58_address).hex()

        # Extract the public key from the decoded address
        public_key = decoded_address[-64:]  # Last 64 characters are the public key

        # Convert the public key to bytes
        public_key_bytes = bytes.fromhex(public_key)

        # Compute the Keccak-256 hash of the public key
        keccak_hash = hashlib.keccak_256(public_key_bytes).hexdigest()

        # Return the public key as a hex string
        return keccak_hash


    def ss58_to_public_key(ss58_address):
        """
        Convert an SS58 coldkey address to a public key.

        Args:
        ss58_address (str): The SS58 encoded address

        Returns:
        str: The public key in hexadecimal format
        """
        try:
            # Create an Ss58Address object
            address = Ss58Address(ss58_address)

            # Get the public key and convert it to hexadecimal
            public_key = address.public_key.hex()

            return public_key
        except ValueError as e:
            print(f"Error: {e}")
            return None

    def ss58_to_public_key2(ss58_address: str) -> str:
        """
        Convert an SS58-encoded cold key address to a public key.

        Args:
            ss58_address (str): The SS58-encoded cold key address.

        Returns:
            str: The corresponding public key.
        """
        # Decode the SS58 address
        decoded_address = base58.b58decode_check(ss58_address).hex()

        # Extract the public key from the decoded address
        public_key = decoded_address[-64:]  # Last 64 characters are the public key

        # Convert the public key to bytes
        public_key_bytes = bytes.fromhex(public_key)

        # Compute the Keccak-256 hash of the public key
        keccak_hash = hashlib.keccak_256(public_key_bytes).hexdigest()

        # Return the public key as a hex string
        return keccak_hash


#print(ss58_to_public_key(coldkey))


#from substrateinterface import Ss58Address

# Example usage
if __name__ == "__main__":
    ss58_address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
    if False:
        public_key = ss58_to_public_key(ss58_address)
        if public_key:
            print(f"SS58 Address: {ss58_address}")
            print(f"Public Key: {public_key}")
    #print(dir(SubstrateInterface))

    if False:
        from substrateinterface import SubstrateInterface
        si = SubstrateInterface(url="wss://rpc.polkadot.io")
        ss58 = "5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"
        publicKey = "0xd092831d050a22a06bf4773fefcbbfdc357ef0e9309125f8f39c2dc50774737a"
        print(ss58, " Should match:", publicKey)
        ss58_decoded = si.ss58_decode(ss58)
        print(ss58_decoded, ss58_decoded==publicKey)
        #print(si.ss58_encode("5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"))
        #print(ss58_to_public_key2("0x5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"))
        if False:
            import codecs
            # Remove the network prefix (first byte)
            # Remove the network prefix (first byte)
            # Remove the network prefix (first byte) and the checksum (last 2 bytes)
            public_key_bytes = ss58_decoded[1:-2]

            # Convert the public key bytes to a hex string
            public_key_hex = '0x' + public_key_bytes.hex()

            print(public_key_hex, public_key_hex==publicKey)

    if True:
        import scalecodec
        from scalecodec.utils.ss58 import ss58_decode
        ss58_address = "5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"
        account_id = ss58_decode(ss58_address, valid_ss58_format=42)
        print(f"The decoded account ID for the address {ss58_address} is: {account_id}")