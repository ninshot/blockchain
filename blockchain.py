"""This python file contains the blockchain class to create new blocks transactions and do hashing of the blocks"""
import hashlib
import json
from datetime import datetime, timezone
from time import time
from urllib.parse import urlparse
import httpx
import pytz
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db import Block, Transaction, Wallet, Node

sask_time = pytz.timezone("America/Regina")

def time_format(dt: datetime | None) -> str | None:
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(sask_time)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

class BlockChain(object):
    async def get_chain(self, session: AsyncSession) -> list[dict]:
        """
        Returns the full chain which exists in the DB
        """
        result = await session.execute(select(Block).order_by(Block.id))
        blocks = result.scalars().unique().all()

        chain: list[dict] = []

        for block in blocks:
            transactions = [
                {
                    "sender" : t.sender,
                    "recipent" : t.recipient,
                    "amount" : t.amount,
                    "signature": t.signature
                }
                for t in block.transactions
            ]

            chain.append({
                "index" : block.id,
                "timestamp" : time_format(block.timestamp),
                "transactions" : transactions,
                "proof": block.proof,
                "previous_hash": block.previous_hash,
            })

        return chain

    async def new_block(self, session: AsyncSession, proof :int, previous_hash:str) -> dict:
        """
        Creates a new block and adds it to the chain
        """
        block = Block(proof=proof, previous_hash=previous_hash)
        session.add(block)
        await session.flush()
        result = await session.execute(select(Transaction).where(Transaction.block_id.is_(None)))
        pending = result.scalars().all()

        for transaction in pending:
            transaction.block_id = block.id

        await session.commit()
        await session.refresh(block)

        transactions = [
            {
                "sender" : t.sender,
                "recipient" : t.recipient,
                "amount" : t.amount,
                "signatur" : t.signature,
            }
            for t in pending
        ]

        return {
            "index" : block.id,
            "timestamp" : time_format(block.timestamp),
            "transactions" : transactions,
            "proof" : block.proof,
            "previous_hash" : block.previous_hash,
        }


    async def new_transaction(self, session : AsyncSession, sender:str, recipient:str, amount:float
                              , signature: str ) -> int:
        """
        Creates a new transaction to go into the next mined block
        """
        if sender != "0":
            sender_wallet = await session.get(Wallet, sender)
            if sender_wallet is None:
                raise ValueError("Wallet doesn't exist")
            if sender_wallet < amount:
                raise ValueError("Sender must be greater than amount")
            sender_wallet.balance -= amount

        recipient_wallet = await session.get(Wallet, recipient)
        if recipient_wallet is None:
            recipient_wallet = Wallet(public_key=recipient, balance=0.0)
            session.add(recipient_wallet)

        recipient_wallet.balance += amount

        new_transaction = Transaction(sender=sender, recipient=recipient,
                        amount=amount, signature=signature, block_id=None)

        session.add(new_transaction)

        result = await session.execute(
            select(Block.id).order_by(Block.id.desc()).limit(1)
        )

        last_block_id = result.scalar_one_or_none()
        last_index = (last_block_id or 0) + 1

        await session.commit()

        return last_index

    @staticmethod
    def hash(block : dict) -> str:
        """
        Creates a SHA-256 hash of a block
        :param block: <dict> Block
        :return: <str> SHA-256 hash
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    async def last_block(self, session : AsyncSession) -> dict | None:
        chain = await self.get_chain(session)
        if not chain:
            return None
        return chain[-1]

    def proof_of_work(self, last_proof:int)-> bool:
        """
        Simple Proof of Work Algorithm :
        -Finds a number p' such that hash(pp') contains leading 4 zeroes, where
        - p is the previous proof, and p' is the new proof
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof:int, proof:int) -> bool:
        """
        Validates the proof: Does hash(last_proof, proof) contain leading 4 zeroes?
        :param last_proof: <int> Previous proof
        :param proof: <int> current proof
        :return: <bool> True if correct, False otherwise
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    async def register_node(self, session: AsyncSession, address:str) -> None:
        """
        Adds a new node to the list of nodes
        :param address: <str> Address of the node, Eg: 'http://127.0.0.1:5001'
        :return: None
        """
        parsed_url = urlparse(address)
        netloc = parsed_url.netloc

        if not netloc:
            raise ValueError("Invalid URL")

        result = await session.execute(select(Node).where(Node.address == netloc))

        existing_node = result.scalar_one_or_none()

        if existing_node is None:
            session.add(Node(address=netloc))
            await session.commit()

    async def get_nodes(self, session : AsyncSession) -> list[str]:
        result = await session.execute(select(Node).order_by(Node.address))
        return [row[0] for row in result.scalars().all()]


    async def valid_chain(self, chain: list[dict]) -> bool:
        """
        Determine if the given blockchain is valid by matching the hashes and validating the proofs of work
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False otherwise
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            #validating the block
            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    async def replace_chain(self, session: AsyncSession, new_chain) -> None:
        "Resolves chain conflicts and replaces them with new chain"

        await session.execute(delete(Transaction))
        await session.execute(delete(Block))
        await session.commit()

        for block in new_chain:
            block = Block(
                proof=block['proof'],
                previous_hash=block['previous_hash'],
                timestamp=datetime.strptime(block['timestamp'], '%Y-%m-%dT%H:%M:%S.%f').replace(
                    tzinfo=timezone)
                if block.get('timestamp')
                else None,

            )
            session.add(block)
            await session.flush()

        for transaction in block.get('transactions', []):
            session.add(
                Transaction(
                    block_id= block.id,
                    sender=transaction['sender'],
                    recipient=transaction['recipient'],
                    amount=transaction['amount'],
                    signature=transaction['signature'],
                )
            )
        await session.commit()


    async def resolve_conflicts(self, session : AsyncSession) -> bool:
        """
        This is our Consensus algorithm. It resolves conflicts
        by replacing our chain with the longest one in the chain.
        :return: <bool> True if the chain was repalced, False otherwise
        """

        neighbours = await self.get_nodes(session)
        current_chain = await self.get_chain(session)
        new_chain: list[dict] | None = None
        max_length = len(current_chain)

        #Verification of nodes

        async with httpx.AsyncClient() as client:
            for node in neighbours:

                    url = f'http://{node}/chain'
                    try:
                        response = await client.get(url, timeout=5.0)

                    except httpx.RequestError:
                        continue

                    if response.status == 200:
                        continue

                    data = response.json()
                    length = data.get['length']
                    chain = data.get['chain']

                    if not isinstance(length, int) or not isinstance(chain, list):
                        continue

                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain


        if new_chain is not None:
            await self.replace_chain(session, new_chain)
            return True

        return False

    def create_wallets(self):
        """"
        A function which helps to generate public and private key to create wallets
        """
        #using rsa generating private key and deriving a public key from private key

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        public_ = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')

        private_ = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()).decode('utf-8')

        public_pem = public_\
                .replace("-----BEGIN PUBLIC KEY-----", "")\
                .replace("-----END PUBLIC KEY-----","")\
                .replace("\n","")

        private_pem = private_\
                    .replace("-----BEGIN RSA PRIVATE KEY-----","")\
                    .replace("-----END RSA PRIVATE KEY-----","")\
                    .replace("\n","")

        return public_pem, private_pem

    @staticmethod
    def sign_transaction(private_key:str,transaction:dict) -> str :
        """
            This function is used to sign a transaction
            @param private_key: <str> Private key
            @param transaction: <dict> Transaction with sender, recipent and the amount
            :return: <str> Transaction signature
        """

        key = serialization.load_pem_private_key(private_key.encode(),
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