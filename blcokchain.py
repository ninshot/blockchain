"""This python file contains the blockchain class to create new blocks transactions and do hashing of the blocks"""
from datetime import time


class BlockChain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []


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

    # a method used for hashing a block
    @staticmethod
    def hash(block):
        pass

    #Returns the last block of the blocks
    def last_block(self):
        pass