# Thanks to the Datura Subnet team for the core signing logic adapted for this script
#     https://github.com/Datura-ai/smart-scrape/blob/develop/datura/scripts/vote_token_signer.py

CYAN = "\033[96m" # field color
GREEN = "\033[92m" # indicating success
RED = "\033[91m" # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
DIVIDER = '_' * 120

import bittensor as bt
import requests
import json
import requests

ss58_decode = None
try:
    from scalecodec.utils.ss58 import ss58_decode
except:
    print("{RED}scalecodec is not installed. Try: pip install scalecodec")

Keypair = None
try:
    from substrateinterface import Keypair
except:
    print("{RED}substrateinterface is not installed. Try: pip install substrateinterface")


class ReadyAiApiLib():
    api_root_url = "https://conversations.xyz"
    api_message_route = "/api/v1/generate_message"
    api_key_route = "/api/v1/generate_api_key"
    minimum_stake = 1.0

    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        if test_mode:
            self.api_root_url = "http://localhost:8000"

    def get_validator_info(self, ss58_coldkey, netuid = 1, verbose=False):
        subnet = bt.metagraph(netuid)
        if not ss58_coldkey in subnet.coldkeys:
            print(f"{RED}Coldkey {ss58_coldkey} not registered on subnet. Aborting.{COLOR_END}")
            if verbose:
                #print("SUBNET COLDKEYS", subnet.coldkeys)
                found_validator_staked = False
                found_validator_unstaked = False
                found_non_validator = False
                for idx, coldkey in enumerate(subnet.coldkeys):
                    if not found_validator_staked and subnet.validator_permit[idx] and subnet.stake[idx] >= self.minimum_stake:
                        print(f"Validator staked: {coldkey} stake: {subnet.stake[idx]}")
                        found_validator_staked = True
                    elif not found_validator_unstaked and subnet.validator_permit[idx] and subnet.stake[idx] < self.minimum_stake:
                        print(f"Validator unstaked: {coldkey} stake: {subnet.stake[idx]}")
                        found_validator_unstaked = True
                    elif not found_non_validator and not subnet.validator_permit[idx]:
                        print(f"Not Validator: {coldkey} stake: {subnet.stake[idx]}")
                        found_non_validator = True
            return
        my_uid = subnet.coldkeys.index( ss58_coldkey )
        print(f"Subnet UID for coldkey: {ss58_coldkey} : {my_uid}")
        if verbose:
            # Display properties for this uid
            self.list_wallets_properties(subnet, uid=my_uid, tensor_len=len(subnet.coldkeys))
        if not ss58_coldkey in subnet.coldkeys:
            print(f"{RED}Coldkey {ss58_coldkey} is not registered in subnet list ({len(subnet.coldkeys)}). Aborting.{COLOR_END}")
            return

        is_validator = bool(subnet.validator_permit[my_uid])
        if not is_validator:
            print(f"{RED}Coldkey is not a validator. Aborting.{COLOR_END}")
            return

        total_stake = float(subnet.stake[my_uid])
        if total_stake < self.minimum_stake:
            print(f"{RED}Total state of {total_stake} is less than minimum stake of {self.minimum_stake}. Aborting.{COLOR_END}")
            return

        validator_info = {"subnet_id": netuid, "uid":my_uid, "coldkey": ss58_coldkey, "hotkey":subnet.hotkeys[my_uid], "is_validator": is_validator, "total_stake":total_stake}
        print(f"{GREEN}COLDKEY {ss58_coldkey} is registered on subnet{COLOR_END}: COLDKEY:{validator_info['coldkey']}, IS VALIDATOR:{validator_info['is_validator']}, TOTAL STAKE:{validator_info['total_stake']}")
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

    def get_api_key_from_coldkey(self, validator_info, coldkey_object):
        message_url = self.api_root_url + self.api_message_route
        key_url = self.api_root_url + self.api_key_route
        # Get one-time-use message that will expire in 10 minutes
        response = self.post_json_to_endpoint(message_url, validator_info)
        if not response:
            return
        message_data = response.json()
        if message_data['success'] != 1:
            print(f"{RED}Error getting message: {message_data['errors']}{COLOR_END}")
            return
        # If successfully generated message, sign message with coldkey
        message = message_data['data']['message']
        signed_message = self.sign_message_with_coldkey(coldkey_object, message)

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
        print(f"\n\n{GREEN}ReadyAI key successfully generated and stored in file: {fname}{COLOR_END}")
        print(f"{YELLOW}    Place this json file in your validator execution directory.{COLOR_END}")


    def sign_message(self, validator_info, message):
        return {"signed":message + "SIGNED"}

    def get_coldkey_object(self, name, path):
        wallet = bt.wallet(name=name, path=path)
        try:
            coldkey = wallet.get_coldkey()
        except Exception as e:
            print(f"{RED}Error loading coldkey: {e} {COLOR_END}")
            exit(1)
        return coldkey

    def sign_message_with_coldkey(self, coldkey_obj, message):
        if self.test_mode:
            return {"signed":message + "SIGNED"}

        signature = coldkey_obj.sign(message.encode("utf-8")).hex()
        keypair = Keypair(ss58_address=coldkey_obj.ss58_address)
        is_valid = keypair.verify(message.encode("utf-8"), bytes.fromhex(signature))
        if not is_valid:
           print(f"{RED}Signature is not valid{COLOR_END}")
           exit(1)
        return {"signed":signature}



if __name__ == "__main__":
    test_mode = True
    raal = ReadyAiApiLib(test_mode)
    cmd = 'test'
    cmd = 'testapi'
    cmd = 'testsign'
    cmd = 'full'

    subnet_str = input(f"{CYAN}Subnet (default=33): {COLOR_END}")
    subnet_id = 33
    try:
        subnet_id = int(subnet_str)
    except:
        pass

    if cmd == 'test':
        if subnet_id == 1:
            ss58_hotkey = '5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3' # Open Tensor Foundation hotkey
        else:
            ss58_hotkey = '5G1awceKsZ4MKTCSkT7qqzhQ5Z3WjWfE5cifCm237Vz3fmN3' # Random validator hotkey
        print(f"{YELLOW}Checking subnet {subnet_id} for hotkey {ss58_hotkey}...{COLOR_END}")
        print(f'{YELLOW}{DIVIDER}{COLOR_END}')
        validator_info = raal.get_validator_info(ss58_hotkey, subnet_id)
        if validator_info:
            validator_info['account_id'] = raal.get_account_from_coldkey(validator_info['coldkey'])
            #print(f"The decoded account ID for the address {ss58_hotkey} is: {validator_info['account_id']}")
            api_info = raal.get_api_key_from_coldkey(validator_info)
    elif cmd == 'testapi':
            validator_info = {}
            api_info = raal.get_api_key_from_coldkey(validator_info)
    elif cmd == 'testsign':
        message = "Shiver me timbers!"
        validator_info = {}
        name = input(f"{CYAN}Enter wallet name (default: Coldkey): {COLOR_END}") or "Coldkey"
        path = input(f"{CYAN}Enter wallet path (default: ~/.bittensor/wallets/): {COLOR_END}") or "~/.bittensor/wallets/"
        coldkey_object = raal.get_coldkey_object(name, path)
        signed_message = raal.sign_message_with_coldkey(coldkey_object, message)
        if signed_message:
            print("signed_message", signed_message)
    elif cmd == 'full':
        if not test_mode:
            name = input(f"{CYAN}Enter wallet name (default: Coldkey): {COLOR_END}") or "Coldkey"
            path = input(f"{CYAN}Enter wallet path (default: ~/.bittensor/wallets/): {COLOR_END}") or "~/.bittensor/wallets/"
            coldkey_object = raal.get_coldkey_object(name, path)
            ss58_coldkey = coldkey_obj.ss58_address
        else:
            coldkey_object = None
            ss58_coldkey = "5HB4EbnVdtmBVdnrUxce2jDE7BJJM1cv9xV1X1wiriyeKy8R" # Not validator
            ss58_coldkey = "5GTVbEdiPtmJ1XWG7FgKaYifLciwWUDDXeauVKgpzKkNDCQL" # Unstaked
            ss58_coldkey = '5GZSAgaVGQqegjhEkxpJjpSVLVmNnE2vx2PFLzr7kBBMKpGQ' # Staked
        print(f"{YELLOW}Checking subnet {subnet_id} for coldkey {ss58_coldkey}...{COLOR_END}")
        print(f'{YELLOW}{DIVIDER}{COLOR_END}')
        validator_info = raal.get_validator_info(ss58_coldkey, subnet_id)
        if validator_info:
            # Coldkey confirmed as validator on subnet with require stake.

            #validator_info['account_id'] = raal.get_account_from_coldkey(validator_info['coldkey'])
            #print(f"The decoded account ID for the address {ss58_hotkey} is: {validator_info['account_id']}")
            api_info = raal.get_api_key_from_coldkey(validator_info, coldkey_object)

