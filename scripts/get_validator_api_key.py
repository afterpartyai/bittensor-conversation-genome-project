import bittensor as bt
import base58
from hashlib import blake2b
from scalecodec.utils.ss58 import ss58_decode
import requests

class CgpApiLib():
    def get(self, ss58_hotkey, netuid = 1, verbose=True):
        subnet = bt.metagraph(netuid)
        if not ss58_hotkey in subnet.hotkeys:
            print(f"Hotkey {ss58_hotkey} not registered on subnet. Aborting.")
            if verbose:
                print("SUBNET HOTKEYS", subnet.hotkeys)
            return
        my_uid = subnet.hotkeys.index( ss58_hotkey )
        print(f"UID for Hotkey: {ss58_hotkey} : {my_uid}")
        if ss58_hotkey not in subnet.hotkeys:
            print(f"Hotkey {ss58_hotkey} is not registered in subnet list ({len(subnet.hotkeys)})")
        else:
            print(f"Hotkey {ss58_hotkey} ")
            print(f"HOTKEY is registered: {subnet.hotkeys[my_uid]}, COLDKEY:{subnet.coldkeys[my_uid]}, VALIDATOR:{subnet.validator_permit[my_uid]}, STAKE:{subnet.stake[my_uid]}")
            coldkey = subnet.coldkeys[my_uid]
            self.list_wallets_properties(subnet, uid=my_uid, tensor_len=len(subnet.hotkeys))

    def list_wallets_properties(self, obj, uid=5, tensor_len=1024):
        properties = dir(obj)
        for prop in properties:
            try:
                value = getattr(obj, prop)
                if len(value) == tensor_len:
                    print(f"{prop}: {value[uid]}")
            except Exception as e:
                pass
                #print(f"{prop}: {e}")


if __name__ == "__main__":
    cmd = 'test'

    if cmd == 'test':
        cal = CgpApiLib()
        print("Subnet (default=33): ",)
        subnet_str = input()
        subnet_id = 33
        try:
            subnet_id = int(subnet_str)
        except:
            pass
        if subnet_id == 1:
            ss58_hotkey = '5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3' # Open Tensor Foundation hotkey
        else:
            ss58_hotkey = '5G1awceKsZ4MKTCSkT7qqzhQ5Z3WjWfE5cifCm237Vz3fmN3' # Random validator hotkey
        print(f"Checking subnet {subnet_id} for hotkey {ss58_hotkey}...")
        cal.get(ss58_hotkey, subnet_id)
        # Works
        #ss58_hotkey = "5GnBLhJG16Ra2WMdKGPUpLopu5wsFPTY6pGyf9u3N1T4cqsC"
        account_id = ss58_decode(ss58_hotkey, valid_ss58_format=42)
        print(f"The decoded account ID for the address {ss58_hotkey} is: {account_id}")

