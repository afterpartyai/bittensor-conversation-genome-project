import bittensor as bt
import base58
from hashlib import blake2b
from scalecodec.utils.ss58 import ss58_decode

class CgpApiLib():
    def get(self, ss58_hotkey, netuid = 1, verbose=False):
        subnet = bt.metagraph(netuid)
        my_uid = subnet.hotkeys.index( ss58_hotkey )
        print(f"UID for Hotkey: {ss58_hotkey} : {my_uid}")
        if verbose:
            print("SUBNET HOTKEYS", subnet.hotkeys)
        if ss58_hotkey not in subnet.hotkeys:
            print(f"Hotkey {ss58_hotkey} is not registered in subnet list ({len(subnet.hotkeys)})")
        else:
            print(f"Hotkey {ss58_hotkey} ")
            print(f"HOTKEY is registered: {subnet.hotkeys[my_uid]}, COLDKEY:{subnet.coldkeys[my_uid]}, VALIDATOR:{subnet.validator_permit[my_uid]}, STAKE:{subnet.stake[my_uid]}")
            coldkey = subnet.coldkeys[my_uid]
            #print("SUBNET",subnet, dir(subnet))
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


if __name__ == "__main__":
    ss58_address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"

    if True:
        cal = CgpApiLib()
        if True:
            subnet = 1
            ss58_hotkey = '5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3' # Open Tensor Foundation hotkey
        else:
            subnet = 33
            ss58_hotkey = '5FbwYitBgj2mySrqpFLgySjpysTPyaht2RfxXMgRcDP4nt2K' # Random validator hotkey

        cal.get(ss58_hotkey, subnet)
        # Works
        ss58_address = "5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"
        account_id = ss58_decode(ss58_address, valid_ss58_format=42)
        print(f"The decoded account ID for the address {ss58_address} is: {account_id}")