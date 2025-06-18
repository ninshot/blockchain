"""This python file contains the blockchain class to create new blocks transactions and do hashing of the blocks"""
import hashlib
import json
from time import time
from urllib.parse import urlparse
import httpx
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
import binascii

from api import private_key


class BlockChain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.new_block(previous_hash=1, proof=100)
        self.nodes = set()
        self.wallets = {}


    def new_block(self, proof, previous_hash=None):
        """
        Creates a new block and adds it to the chain
        :param proof: <int> The proof given by the proof of work algorithm
        :param previous_hash: (Optional) <str> Hash of previous block
        :return: <dict> New block
        """
        block={
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.current_transactions = []
        self.chain.append(block)
        return block


    def new_transaction(self, sender, recipient, amount, signature):
        """
        Creates a new transaction to go into the next mined block
        :param sender: <str> sender's address'
        :param recipient: <str> recipient's address'
        :param amount: <int> amount of money
        :return: <int> index of the  block which holds the new transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'signature' : signature
        })

        return self.last_block['index'] + 1

    def get_transaction(self, recipient):
        """
        Used to get a particular transaction send to a recipent
        :param recipient: <str> recipient address
        :return: <dict> the transaction
        """

        for transaction in self.current_transactions:
            if transaction['recipient'] == recipient:
                return transaction

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a block
        :param block: <dict> Block
        :return: <str> SHA-256 hash
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm :
        -Finds a number p' such that hash(pp') contains leading 4 zeroes, where
        - p is the previous proof, and p' is the new proof
        :param last_proof: <int> Last proof given by the proof of work
        :return: <int> New proof given by the proof of work
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the proof: Does hash(last_proof, proof) contain leading 4 zeroes?
        :param last_proof: <int> Previous proof
        :param proof: <int> current proof
        :return: <bool> True if correct, False otherwise
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    def register_node(self, address):
        """
        Adds a new node to the list of nodes
        :param address: <str> Address of the node, Eg: 'http://127.0.0.1:5001'
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


    def valid_chain(self, chain):
        """
        Determine if the given blockchain is valid by matching the hashes and validating the proofs of work
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False otherwise
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n---------------------\n")

            #validating the block
            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    async def resolve_conflicts(self):
        """
        This is our Consensus algorithm. It resolves conflicts
        by replacing our chain with the longest one in the chain.
        :return: <bool> True if the chain was repalced, False otherwise
        """

        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        #Verification of nodes

        async with httpx.AsyncClient() as client:
            for node in neighbours:
                try:
                    url = f'http://{node}/'
                    response = await client.get(url)
                    if response.status == 200:
                        data = await response.json()
                        length = data['length']
                        chain = data['chain']

                        if length > max_length and self.valid_chain(chain):
                            max_length = length
                            new_chain = chain
                except Exception as e:
                    print(f'Exception: {e}')
                    continue

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def create_wallets(self):
        """"
        A function which helps to generate public and private key to create wallets
        """
        #using rsa generating private key and deriving a public key from private key

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')

        private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()).decode('utf-8')

        return public_pem, private_pem

    @staticmethod
    def sign_transaction(priavte_key:str, transaction: dict) -> str:
        """
            This function is used to sign a transaction
            @param priavte_key: <str> Private key
            @param transaction: <dict> Transaction with sender, recipent and the amount
            :return: <str> Transaction signature
        """

        key = serialization.load_pem_private_key(priavte_key.encode(),
                password=None)

        """
        This block of code basically creates the signature by breaking down the transaction dict into
        JSON formatted string, and then encoding it into bytes, then adds the PSS pading for extra security to the key,
        so that it cant be decrypted easily and hashes it in SHA-256 hash internally.
        """
        signature = key.sign(json.dumps(transaction, sort_keys=True).encode(),
                             padding.PKCS1v15(),
                             hashes.SHA256()
                             )

        return signature.hex()

    @staticmethod
    def verify_transaction(public_key:str, transaction:dict, signature: str) -> bool:
        """
        This function is used to verify a transaction
        :param public_key: PEM encoded public key
        :param transaction: dict with a sender, recipent and the amount
        :param signature: hex encoded signature
        :return: true if the transaction is valid, false otherwise
        """

        try:
            public_key = serialization.load_pem_public_key(public_key.encode())
            public_key.verify(bytes.fromhex(signature),
                              json.dumps(transaction, sort_keys=True).encode(),
                              padding.PKCS1v15(),
                              hashes.SHA256()
                              )
            return True

        except Exception as e:
            print(f'Exception: {e}')
            return False


