"""This python file contains the blockchain class to create new blocks transactions and do hashing of the blocks"""
import hashlib
import json
from cgitb import reset
from time import time
from uuid import uuid4
from flask import Flask, jsonify
from textwrap import dedent


class BlockChain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.new_block(previous_hash=1, proof=100)


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


    def new_transaction(self, sender, recipient, amount):
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
        })

        return self.last_block['index'] + 1


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
        while self.validproof(last_proof, proof) is False:
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

#Intiation of our Node
app = Flask(__name__)

#Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

#Intiation of blockchain
blockchain = BlockChain()

@app.route('/mine', methods=['GET'])
def mine():
    return "We will mine a new block"

@app.route('/transactions/new', methods=['POST'])
def transactions():
    return "Addition of new Transaction"

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)