"""This python file contains the blockchain class to create new blocks transactions and do hashing of the blocks"""

class BlockChain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

    #A Method used for creation of a new block and adds it to the chain
    def new_block(self):
        pass

    #A method used for creation of new transaction and add them to a list
    def new_transaction(self):
        pass

    # a method used for hashing a block
    @staticmethod
    def hash(block):
        pass

    #Returns the last block of the blocks
    def last_block(self):
        pass