CYAN = "\033[96m" # field color
GREEN = "\033[92m" # indicating success
RED = "\033[91m" # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
DIVIDER = '_' * 120

import bittensor as bt
import requests
import json

ss58_decode = None
try:
    from scalecodec.utils.ss58 import ss58_decode
except:
    print("{RED}scalecodec is not installed. Try: pip install xxx")
import requests

from substrateinterface import Keypair

class CgpApiLib():
    api_root_url = "http://localhost:8000"
    api_message_route = "/api/v1/generate_message"
    api_key_route = "/api/v1/generate_api_key"

    def get_validator_info(self, ss58_hotkey, netuid = 1, verbose=False):
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
            validator_info = {"subnet_id": netuid, "uid":my_uid, "hotkey": ss58_hotkey, "coldkey":subnet.coldkeys[my_uid], "is_validator": bool(subnet.validator_permit[my_uid]), "total_stake":float(subnet.stake[my_uid])}
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

    def post_json_to_endpoint(self, url, json_body):
        try:
            json_body_str = json.dumps(json_body)

            headers = {'Content-Type': 'application/json'}

            response = requests.post(url, data=json_body_str, headers=headers, timeout=30)

            if response.status_code >= 400:
                print(f"{RED}Error posting to {url}: {response.status_code} - {response.text}{COLOR_END}")
                return

            return response

        except requests.exceptions.RequestException as e:
            print(f"{RED}Error posting to {url}: {e}{COLOR_END}")

    def get_api_key_from_coldkey(self, validator_info):
        print(f"{YELLOW}POST {validator_info}{COLOR_END}")
        message_url = self.api_root_url + self.api_message_route
        key_url = self.api_root_url + self.api_key_route
        response = self.post_json_to_endpoint(message_url, validator_info)
        if not response:
            return
        message_data = response.json()
        if message_data['success'] != 1:
            print(f"{RED}Error: {message_data['errors']}{COLOR_END}")
            return
        message = message_data['data']['message']
        signed_message = self.sign_message({}, message)

        response_key = self.post_json_to_endpoint(key_url, signed_message)
        if not response_key:
            return
        key_data = response_key.json()
        if key_data['success'] != 1:
            print(f"{RED}Keygen Error: {key_data['errors']}{COLOR_END}")
            return
        api_key_data = key_data['data']
        fname = "readyai_api_data.json"
        f = open(fname, 'w')
        f.write(json.dumps(api_key_data))
        f.close()
        print(f"{GREEN}ReadyAI key successfully generated and stored in file: {fname}{COLOR_END}")
        print(f"{YELLOW}    Place this json file in your validator execution directory.{COLOR_END}")


    def sign_message(self, validator_info, message):
        return {"signed":message + "SIGNED"}




if __name__ == "__main__":
    cal = CgpApiLib()
    cmd = 'test'
    cmd = 'testapi'
    cmd = 'testsign'

    if cmd == 'test':
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
        validator_info = cal.get_validator_info(ss58_hotkey, subnet_id)
        if validator_info:
            validator_info['account_id'] = cal.get_account_from_coldkey(validator_info['coldkey'])
            #print(f"The decoded account ID for the address {ss58_hotkey} is: {validator_info['account_id']}")
            api_info = cal.get_api_key_from_coldkey(validator_info)
    elif cmd == 'testapi':
            validator_info = {}
            api_info = cal.get_api_key_from_coldkey(validator_info)
    elif cmd == 'testsign':
            message = "Shiver me timbers!"
            validator_info = {}
            name = input(f"{CYAN}Enter wallet name (default: Coldkey): {COLOR_END}") or "Coldkey"
            path = input(f"{CYAN}Enter wallet path (default: ~/.bittensor/wallets/): {COLOR_END}") or "~/.bittensor/wallets/"
            wallet = bt.wallet(name=name, path=path)
            try:
                coldkey = wallet.get_coldkey()
            except Exception as e:
                print(f"{RED}Error loading coldkey: {e} {COLOR_END}")
                exit(1)
            signature = coldkey.sign(message.encode("utf-8")).hex()
            keypair = Keypair(ss58_address=coldkey.ss58_address)
            is_valid = keypair.verify(message.encode("utf-8"), bytes.fromhex(signature))
            if not is_valid:
               print(f"{RED}Signature is not valid{COLOR_END}")
               exit(1)
            print(signature)

            #signed_message = cal.sign_message(validator_info, message)
            #print("signed_message", signed_message)


