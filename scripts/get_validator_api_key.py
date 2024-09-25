import bittensor as bt
import base58
from hashlib import blake2b
from scalecodec.utils.ss58 import ss58_decode

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
        self.list_wallets_properties(subnet)

    def list_wallets_properties(self, obj):
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





#print(ss58_to_public_key(coldkey))


#from substrateinterface import Ss58Address

# Example usage
if __name__ == "__main__":
    ss58_address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"

    if False:
        # Works but keys don't match
        from substrateinterface import SubstrateInterface
        si = SubstrateInterface(url="wss://rpc.polkadot.io")
        ss58 = "5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"
        publicKey = "0xd092831d050a22a06bf4773fefcbbfdc357ef0e9309125f8f39c2dc50774737a"
        print(ss58, " Should match:", publicKey)
        ss58_decoded = si.ss58_decode(ss58)
        print(ss58_decoded, ss58_decoded==publicKey)
        #print(si.ss58_encode("5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"))
        #print(ss58_to_public_key2("0x5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"))

    if True:
        cal = CgpApiLib()
        cal.get()
        # Works
        ss58_address = "5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"
        account_id = ss58_decode(ss58_address, valid_ss58_format=42)
        print(f"The decoded account ID for the address {ss58_address} is: {account_id}")