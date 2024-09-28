import random
import json
import requests
import sys
import logging
import argparse
import os
import time

parser = argparse.ArgumentParser(description="Python script to initialize and unseal Vault")
parser.add_argument('--vault_url', help="Vault URL", default=os.environ.get('VAULT_URL'), type=str)
parser.add_argument('--unseal_threshold', help="Unseal threshold", default=int(os.environ.get('UNSEAL_THRESHOLD', 3)), type=int)
parser.add_argument('--recovery_shares', help="Recovery shares", default=int(os.environ.get('RECOVERY_SHARES', 7)), type=int)
args = parser.parse_args()

vault_url = args.vault_url
unseal_threshold = args.unseal_threshold
recovery_shares = args.recovery_shares

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')

def service_check(vault_url):
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = requests.get(f"{vault_url}/v1/sys/health")
            if response.status_code == 200:
                logging.info("Vault is initialized and active")
                break
            elif response.status_code == 501:
                logging.info("Vault is not initialized, starting initialization")
                init_vault(vault_url, unseal_threshold, recovery_shares)
                break
            elif response.status_code == 503:
                logging.info("Vault is sealed, starting unseal process")
                unseal_vault(vault_url, unseal_threshold)
                break
        except requests.exceptions.ConnectionError:
            logging.warning(f"Vault is not reachable, retrying in 5 seconds...")
            retry_count += 1
            time.sleep(5)

    if retry_count == max_retries:
        logging.error("Max retries exceeded, Vault service is still unavailable.")
        sys.exit(1)

def init_vault(vault_url, unseal_threshold, recovery_shares):
    response = requests.post(f"{vault_url}/v1/sys/init", json = {"secret_shares": recovery_shares, "secret_threshold": unseal_threshold})

    if response.status_code == 200:
        data = response.json()
        logging.info(f"Vault initialized successfully")
        logging.info(f"Response code: {response.status_code}")
        with open('/unseal/.unseal', 'w') as file:
            json.dump(data, file)
        unseal_vault(vault_url, unseal_threshold)
    else:
        logging.error(f"Failed to initialize vault")
        logging.error(f"Response code: {response.status_code}")
        logging.error(f"Response: {response.text}")
        print("-" * 80)
        sys.exit(1)

def unseal_vault(vault_url, unseal_threshold):
    try:
        status_response = requests.get(f"{vault_url}/v1/sys/seal-status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            secret_threshold = status_data.get('t', 0)
            progress = status_data.get('progress', 0)
        else:
            logging.error(f"Failed to retrieve Vault status. Response code: {status_response.status_code}")
            print("-" * 80)
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error occurred while retrieving Vault status: {str(e)}")
        print("-" * 80)
        sys.exit(1)

    try:
        with open('/unseal/.unseal') as file:
            data = json.load(file)
    except FileNotFoundError:
        logging.error(f"Unseal file not found. Initialization might have failed.")
        print("-" * 80)
        sys.exit(1)
    
    unseal_list = data['keys_base64'] or data['key']
    if not unseal_list:
        logging.error("No unseal keys found in the file.")
        print("-" * 80)
        sys.exit(1)

    random_keys = random.sample(unseal_list, unseal_threshold)

    for key in random_keys:
        response = requests.put(f"{vault_url}/v1/sys/unseal", json={"key": key})

        if response.status_code == 200:
            response_data = response.json()
            sealed_status = response_data.get('sealed', True)
            progress = response_data.get('progress', 0)

            if not sealed_status:
                logging.info("Vault unsealed successfully")
                logging.info(f"Response code: {response.status_code}")
                print("-" * 80)
                return True
            else:
                continue
        else:
            logging.error(f"Failed to send unseal request")
            logging.error(f"Response code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            print("-" * 80)

    if unseal_threshold < secret_threshold:
        logging.error(f"Vault is still sealed after unseal attempts. Progress: {progress}/{secret_threshold}")
        print("-" * 80)
        sys.exit(1)

if __name__ == "__main__":
    service_check(vault_url)