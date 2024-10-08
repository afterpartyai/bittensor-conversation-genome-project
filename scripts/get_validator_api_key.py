# Thanks to the Datura Subnet team for the core signing logic adapted for this script
#     https://github.com/Datura-ai/smart-scrape/blob/develop/datura/scripts/vote_token_signer.py

CYAN = "\033[96m" # field color
GREEN = "\033[92m" # indicating success
RED = "\033[91m" # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
DIVIDER = '_' * 120

import bittensor as bt
import sys
import requests
import json
import requests


Keypair = None
try:
    from substrateinterface import Keypair
except:
    print(f"{RED}substrateinterface is not installed. Try: pip install substrateinterface{COLOR_END}")


class ReadyAiApiLib():
    #api_root_url = "https://api.conversations.xyz"
    api_root_url = "http://dan.soindrop.com"
    api_message_route = "/api/v1/generate_message"
    api_key_route = "/api/v1/generate_api_key"
    network = 'finney'
    minimum_stake = 20000.0
    verbose = False

    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        if False and test_mode:
            self.api_root_url = "http://localhost:8000"

    def report_valid_accounts(self, wallet_key, keys, subnet):
        #print("SUBNET COLDKEYS", subnet.coldkeys)
        found_validator_staked = False
        found_validator_unstaked = False
        found_non_validator = False
        for wallet_key in keys:
            test_uid = keys.index( wallet_key )
            is_test_validator = bool(subnet.validator_permit[test_uid])
            if not found_validator_staked and is_test_validator and subnet.stake[test_uid] >= self.minimum_stake:
                print(f"Validator {test_uid} staked: {wallet_key} validator:{subnet.validator_permit[test_uid]} stake: {subnet.stake[test_uid]}")
                found_validator_staked = True
            elif not found_validator_unstaked and is_test_validator and subnet.stake[test_uid] < self.minimum_stake:
                print(f"Validator {test_uid} unstaked: {wallet_key} validator:{subnet.validator_permit[test_uid]} stake: {subnet.stake[test_uid]}")
                found_validator_unstaked = True
            elif not found_non_validator and not subnet.validator_permit[test_uid]:
                print(f"Not Validator {test_uid} : {wallet_key} stake: {subnet.stake[test_uid]}")
                found_non_validator = True


    def get_validator_info(self, ss58_coldkey=None, ss58_hotkey=None, netuid=1, verbose=False):
        subnet = bt.metagraph(netuid, network=self.network)
        if ss58_coldkey and not ss58_coldkey in subnet.coldkeys:
            print(f"{RED}Coldkey {ss58_coldkey} not registered on subnet. Aborting.{COLOR_END}")
            if self.verbose or verbose:
                self.report_valid_accounts(ss58_coldkey, subnet.coldkeys, subnet)
            return
            my_uid = subnet.coldkeys.index( ss58_coldkey )

            # Find stakes across all hotkeys
            total_stake = 0.0
            stake = 0.0
            max_stake = 0.0
            is_validator = False
            for idx, ck in enumerate(subnet.coldkeys):
                if ss58_coldkey == ck:
                    #self.list_wallets_properties(subnet, uid=my_uid, tensor_len=len(subnet.coldkeys))
                    total_stake += float(subnet.total_stake[idx])
                    max_stake = max(max_stake, float(subnet.total_stake[idx]))
                    stake += float(subnet.stake[idx])
                    if bool(subnet.validator_permit[idx]):
                        is_validator = True
                    #print("FOUND!", subnet.coldkeys[idx], subnet.hotkeys[idx], subnet.stake[idx], subnet.total_stake[idx], subnet.validator_permit[idx])

        else:
            if not ss58_hotkey or (ss58_hotkey and not ss58_hotkey in subnet.hotkeys):
                print(f"{RED}Hotkey {ss58_coldkey} not registered on subnet. Aborting.{COLOR_END}")
                if self.verbose or verbose:
                    self.report_valid_accounts(ss58_coldkey, subnet.hotkeys, subnet)
                return
            my_uid = subnet.hotkeys.index( ss58_hotkey )
            total_stake = float(subnet.total_stake[my_uid])
            max_stake = float(subnet.total_stake[my_uid])
            stake = float(subnet.stake[my_uid])
            if bool(subnet.validator_permit[my_uid]):
                is_validator = True



        print(f"Subnet UID for wallet key -- coldkey: {ss58_coldkey} hotkey: {ss58_hotkey} : {my_uid}")
        if self.verbose or verbose:
            # Display properties for this uid
            self.list_wallets_properties(subnet, uid=my_uid, tensor_len=len(subnet.coldkeys))

        if (ss58_coldkey and not ss58_coldkey in subnet.coldkeys) and (ss58_hotkey and not ss58_hotkey in subnet.hotkeys):
            print(f"{RED}Key {ss58_coldkey} or {ss58_hotkey} is not registered in subnet list ({len(subnet.coldkeys)}). Aborting.{COLOR_END}")
            return

        if not is_validator:
            print(f"{RED}Key {my_uid} is not a validator : {is_validator}. Aborting.{COLOR_END}")
            return

        if max_stake < self.minimum_stake:
            print(f"{RED}Total state of {total_stake} is less than minimum stake of {self.minimum_stake}. Aborting.{COLOR_END}")
            return

        lookup_coldkey = None
        lookup_hotkey = None
        if ss58_coldkey:
            lookup_hotkey = subnet.hotkeys[my_uid]
        else:
            lookup_coldkey = subnet.hotkeys[my_uid]
        validator_info = {
            "subnet_id": netuid,
            "uid":my_uid,
            "coldkey": ss58_coldkey,
            "hotkey": ss58_hotkey,
            "lookup_coldkey": lookup_coldkey,
            "lookup_hotkey": lookup_hotkey,
            "is_validator": is_validator,
            "stake":stake,
            "total_stake":total_stake
        }
        if ss58_coldkey:
            print(f"{GREEN}COLDKEY {ss58_coldkey} is registered on subnet{COLOR_END}: COLDKEY:{validator_info['coldkey']}, IS VALIDATOR:{validator_info['is_validator']}, TOTAL STAKE:{validator_info['total_stake']}")
        else:
            print(f"{GREEN}HOTKEY {ss58_hotkey} is registered on subnet{COLOR_END}: HOTKEY:{validator_info['hotkey']}, IS VALIDATOR:{validator_info['is_validator']}, TOTAL STAKE:{validator_info['total_stake']}")

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

    def get_api_key(self, validator_info, coldkey_object=None, hotkey_object=None, verbose=False):
        # Setup URL to get message from API that will be signed by coldkey
        message_url = self.api_root_url + self.api_message_route

        # After message is signed, confirm with API and get API key
        key_url = self.api_root_url + self.api_key_route
        if self.verbose or verbose:
            print(f"URLs: message: {message_url} key:{key_url}")

        # Get one-time-use message to sign that will expire in 10 minutes
        response = self.post_json_to_endpoint(message_url, validator_info)
        if not response:
            return

        message_data = response.json()

        if self.verbose or verbose:
            print(f"Message returned from API: {message_data}")
        if message_data['success'] != 1:
            print(f"{RED}Error getting message: {message_data['errors']} from {message_url}{COLOR_END}")
            return

        # If successfully obtained message, sign message with coldkey
        message = message_data['data']['message']
        print(f"Signing message...")
        signed_message = self.sign_message(coldkey_object=coldkey_object, hotkey_object=hotkey_object, message=message)
        validator_info['message'] = message
        validator_info['signed_message'] = signed_message
        print(f"Signed. Get API key...")
        response_key = self.post_json_to_endpoint(key_url, validator_info)
        if not response_key:
            return
        key_data = response_key.json()
        if key_data['success'] != 1:
            print(f"{RED}Error from keygen endpoint: {key_data['errors']}{COLOR_END}")
            return
        api_key_data = key_data['data']
        print(f"{YELLOW}Got API key, writing to file...{COLOR_END}")
        if self.verbose or verbose:
            print("API KEY", api_key_data)
        fname = "readyai_api_data.json"
        f = open(fname, 'w')
        f.write(json.dumps(api_key_data))
        f.close()
        print(f"\n\n{GREEN}ReadyAI key successfully generated and stored in file: {fname}{COLOR_END}")
        print(f"{YELLOW}    Place this json file in your validator execution directory.{COLOR_END}")


    def get_coldkey_object(self, name, path):
        wallet = bt.wallet(name=name, path=path)
        try:
            coldkey = wallet.get_coldkey()
        except Exception as e:
            print(f"{RED}Error loading coldkey: {e} {COLOR_END}")
            exit(1)
        return coldkey

    def get_hotkey_object(self, coldkey_name, hotkey_name, path):
        wallet = bt.wallet(name=coldkey_name, hotkey=hotkey_name, path=path)
        try:
            hotkey = wallet.get_hotkey()
        except Exception as e:
            print(f"{RED}Error loading hotkey: {e} {COLOR_END}")
            exit(1)
        return hotkey

    def sign_message(self, coldkey_object=None, hotkey_object=None, message=None):
        # For testmode that isn't generating a key, include a fake signed key
        if self.test_mode and not coldkey_object and not hotkey_object:
            signed_message = {"signed":message + "SIGNED"}
            validator_info['signed'] = "eca79a777366194d9eef83379b413b1c6349473ed0ca19bc7f33e2c0461e0c75ccbd25ffdd6e25b93ee2c7ac6bf80815420ddb8c61e8c5fc02dfa27ba105b387"
            validator_info['coldkey'] = "5EhPJEicfJRF6EZyq82YtwkFyg4SCTqeFAo7s5Nbw2zUFDFi"
            return signed_message

        if coldkey_object:
            signature = coldkey_object.sign(message.encode("utf-8")).hex()
            keypair = Keypair(ss58_address=coldkey_object.ss58_address)
        else:
            signature = hotkey_object.sign(message.encode("utf-8")).hex()
            keypair = Keypair(ss58_address=hotkey_object.ss58_address)
        is_valid = keypair.verify(message.encode("utf-8"), bytes.fromhex(signature))
        if self.verbose:
            print("MSG", message, signature)
        if not is_valid:
            print(f"{RED}Signature is not valid{COLOR_END}")
            exit(1)
        else:
            print(f"{GREEN}Signature is valid{COLOR_END}")
        return {"signed":signature}



if __name__ == "__main__":
    print(f"\n{CYAN}____ Generate ReadyAI Validator API key ____{COLOR_END}\n")
    print(f"Follow prompts below to generate an API key for validator access to the ReadyAI Conversation Server. Once successfully generated, your API key will live in the .readyai_ai_data.json file in the top-level folder of the ReadyAI SN33 repository. For more details, please see the documentation in docs/generate-validator-api-key.md\n")
    subnet_id = 33
    sign_with_coldkey = False

    args = sys.argv[1:] + [''] * 10
    network = args[0]
    test_mode_num = args[1]
    if sign_with_coldkey:
        test_cold_key = args[2]
        test_hot_key = None
    else:
        test_cold_key = None
        test_hot_key = args[2]
    test_mode = False

    # test_mode_num 1 = Run with specified key without signing message (mock signed message)
    # test_mode_num 2 = Sign message, but allow any key (doesn't check for validator stake, etc.)
    if test_mode_num == "1" or test_mode_num == "2":
        print(f"{YELLOW}*** Test mode {test_mode_num} ***{COLOR_END}")
        subnet_id = 138
        test_mode = True
    raal = ReadyAiApiLib(test_mode)

    # No network specified or '-', run against finney mainnet
    if len(network) > 0 and network != '-':
        print(f"{YELLOW}Set network to: {network}{COLOR_END}")
        raal.network = network
        if network == 'test':
            raal.minimum_stake = 10.0
            print(f"{YELLOW}Set test stake to: {raal.minimum_stake}{COLOR_END}")

    # Get user input of subnet id
    subnet_str = input(f"{CYAN}Subnet (default={subnet_id}): {COLOR_END}")
    try:
        subnet_id = int(subnet_str)
    except:
        pass

    ss58_coldkey = None
    ss58_hotkey = None
    coldkey_object = None
    hotkey_object = None
    # If actual run or test_mode_num == 2, prompt for wallet
    if not test_mode or test_mode_num == "2":
        path = input(f"{CYAN}Enter wallet path (default: ~/.bittensor/wallets/): {COLOR_END}") or "~/.bittensor/wallets/"

        defaultWallet = "Coldkey"
        coldkey_name = input(f"{CYAN}Enter wallet name (default: {defaultWallet}): {COLOR_END}") or defaultWallet

        if not sign_with_coldkey:
            defaultWallet = "default"
            hotkey_name = input(f"{CYAN}Enter hotkey name (default: {defaultWallet}): {COLOR_END}") or defaultWallet

        if sign_with_coldkey:
            coldkey_object = raal.get_coldkey_object(coldkey_name, path)
            ss58_coldkey = coldkey_object.ss58_address
        else:
            hotkey_path = f"{path}"
            hotkey_object = raal.get_hotkey_object(coldkey_name, hotkey_name, path)
            ss58_hotkey = hotkey_object.ss58_address
    else:
        raal.verbose = True
        coldkey_object = None
        ss58_coldkey = test_cold_key
        ss58_hotkey = test_hot_key

    if ss58_coldkey:
        print(f"{YELLOW}Checking subnet {subnet_id} for coldkey {ss58_coldkey}...{COLOR_END}")
    else:
        print(f"{YELLOW}Checking subnet {subnet_id} for hotkey {ss58_hotkey}...{COLOR_END}")

    print(f'{YELLOW}{DIVIDER}{COLOR_END}')

    if test_mode_num == "2":
        validator_info = {"test_mode":2, "hotkey": ss58_hotkey, "coldkey": ss58_coldkey, "subnet_id": subnet_id,  "uid": 11,  }
    else:
        validator_info = raal.get_validator_info(ss58_hotkey=ss58_hotkey, ss58_coldkey=ss58_coldkey, netuid=subnet_id)

    if validator_info:
        api_info = raal.get_api_key(validator_info, hotkey_object=hotkey_object, coldkey_object=coldkey_object)

