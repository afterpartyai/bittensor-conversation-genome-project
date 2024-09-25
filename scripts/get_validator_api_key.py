CYAN = "\033[96m" # field color
GREEN = "\033[92m" # indicating success
RED = "\033[91m" # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
DIVIDER = '_' * 120

import bittensor as bt
import base58
from hashlib import blake2b

ss58_decode = None
try:
    from scalecodec.utils.ss58 import ss58_decode
except:
    print("{RED}scalecodec is not installed. Try: pip install xxx")
import requests



class CgpApiLib():
    def get(self, ss58_hotkey, netuid = 1, verbose=False):
        subnet = bt.metagraph(netuid)
        if not ss58_hotkey in subnet.hotkeys:
            print(f"{RED}Hotkey {ss58_hotkey} not registered on subnet. Aborting.{COLOR_END}")
            if verbose:
                print("SUBNET HOTKEYS", subnet.hotkeys)
            return
        my_uid = subnet.hotkeys.index( ss58_hotkey )
        print(f"UID for Hotkey: {ss58_hotkey} : {my_uid}")
        if ss58_hotkey not in subnet.hotkeys:
            print(f"{RED}Hotkey {ss58_hotkey} is not registered in subnet list ({len(subnet.hotkeys)}). Aborting.{COLOR_END}")
            return
        else:
            validator_info = {"subnet_id": netuid, "uid":my_uid, "hotkey": ss58_hotkey, "coldkey":subnet.coldkeys[my_uid], "is_validator": subnet.validator_permit[my_uid], "total_stake":subnet.stake[my_uid]}
            print(f"{GREEN}HOTKEY {ss58_hotkey} is registered on subnet{COLOR_END}: COLDKEY:{validator_info['coldkey']}, IS VALIDATOR:{validator_info['is_validator']}, TOTAL STAKE:{validator_info['total_stake']}")
            if verbose:
                # Display properties for this uid
                self.list_wallets_properties(subnet, uid=my_uid, tensor_len=len(subnet.hotkeys))
            return validator_info


    def list_wallets_properties(self, obj, uid=5, tensor_len=1024):
        properties = dir(obj)
        for prop in properties:
            try:
                value = getattr(obj, prop)
                if len(value) == tensor_len:
                    print(f"{YELLOW}{prop}{COLOR_END}: {value[uid]}")
            except Exception as e:
                pass
                #print(f"{prop}: {e}")

    def get_account_from_coldkey(self, ss58_coldkey):
        if not ss58_decode:
            print("{RED}scalecodec is not installed. Aborting.")
            return
        return ss58_decode(ss58_coldkey, valid_ss58_format=42)


if __name__ == "__main__":
    cmd = 'test'

    if cmd == 'test':
        cal = CgpApiLib()
        subnet_str = input(f"{CYAN}Subnet (default=33): {COLOR_END}")
        subnet_id = 33
        try:
            subnet_id = int(subnet_str)
        except:
            pass
        if subnet_id == 1:
            ss58_hotkey = '5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3' # Open Tensor Foundation hotkey
        else:
            ss58_hotkey = '5G1awceKsZ4MKTCSkT7qqzhQ5Z3WjWfE5cifCm237Vz3fmN3' # Random validator hotkey
        print(f"{YELLOW}Checking subnet {subnet_id} for hotkey {ss58_hotkey}...{COLOR_END}")
        print(f'{YELLOW}{DIVIDER}{COLOR_END}')
        validator_info = cal.get(ss58_hotkey, subnet_id)
        account_id = cal.get_account_from_coldkey(ss58_hotkey)
        print(f"The decoded account ID for the address {ss58_hotkey} is: {account_id}")

