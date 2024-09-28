# vault-script
Script for automatic initialization and unseal of vault service


### Running a script outside the docker shell
|docker env | python key | description |
| ---       | ---        | ----------- |
| VAULT_URL        | --vault_url        | |
| UNSEAL_THRESHOLD | --unseal_threshold | |
| RECOVERY_SHARES  | --recovery_shares  | Number of keys to be generated during service initialization |

##### example
```sh
python3 main.py \
--vault_url 'http://vault.example.local' \
--unseal_threshold 3 \
--recovery_shares 7
```