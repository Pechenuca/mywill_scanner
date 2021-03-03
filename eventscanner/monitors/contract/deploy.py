from scanner.events.block_event import BlockEvent
from mywish_models.models import ETHContract, Contract, Network, session
from blockchain_common.wrapper_transaction import WrapperTransaction
from eventscanner.queue.pika_handler import send_to_backend
from blockchain_common.base_monitor import BaseMonitor

from settings.settings_local import NETWORKS


class DeployMonitor(BaseMonitor):
    event_type = 'deployed'

    def on_new_block_event(self, block_event: BlockEvent):
        if block_event.network.type != self.network_type:
            return

        deploy_hashes = {}
        for transactions_list in block_event.transactions_by_address.values():
            for transaction in transactions_list:
                if transaction.contract_creation:
                    deploy_hashes[transaction.tx_hash.lower()] = transaction

        eth_contracts = session.query(ETHContract, Contract, Network)\
            .filter(Contract.id == ETHContract.contract_id, Contract.network_id == Network.id)\
            .filter(ETHContract.tx_hash.in_(deploy_hashes.keys()))\
            .filter(Network.name == block_event.network.type).all()

        for contract in eth_contracts:
            print("eth_id:", contract[0].id, "contract_id", contract[0].contract_id, contract[0].tx_hash)
            transaction: WrapperTransaction = deploy_hashes[contract[0].tx_hash]
            tx_receipt = block_event.network.get_tx_receipt(transaction.tx_hash)

            message = {
                'contractId': contract[0].id,
                'transactionHash': transaction.tx_hash,
                'address': transaction.creates,
                'success': tx_receipt.success,
                'status': 'COMMITTED'
            }

            send_to_backend(self.event_type, NETWORKS[block_event.network.type]['queue'], message)
