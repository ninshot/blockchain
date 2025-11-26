"""
This file contains the api endpoints build using REST through Fastapi

"""
import uuid
from uuid import uuid4
from fastapi import FastAPI,HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select

from blockchain import BlockChain
from fastapi.middleware.cors import CORSMiddleware
from db import Wallet, Node, Transaction, Block, create_db_and_tableS,get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

#Intiation of our Node
@asynccontextmanager
async def lifespan(app:FastAPI):
    await create_db_and_tableS()
    yield
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Intiation of blockchain
blockchain = BlockChain()
node_identifier: str | None = None

@app.post("/wallet/create")
async def create_wallet(
        session: AsyncSession = Depends(get_async_session),
):
    global node_identifier

    public_key, private_key = blockchain.create_wallets()
    node_identifier = public_key

    existing = await session.get(Wallet, public_key)
    if existing is None:
        wallet = Wallet(public_key = public_key, balance=0.0)
        session.add(wallet)
        await session.commit()

    response = {
        "data" : {
            "publicKey" : public_key,
            "privateKey" : private_key
        }
    }
    return JSONResponse(content={"status" : "success", "data" :response},status_code=200)

@app.get("/mine")
async def mine(
        session: AsyncSession = Depends(get_async_session),
):
    if node_identifier is None:
        return JSONResponse(
            content={"status" : "Error", "message" : "No Wallet found"}, status_code=400
        )

    result = await session.execute(
        select(Block).order_by(Block.id.desc()).limit(1)
    )

    last_block = result.scalar_one_or_none()
    last_proof = last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    reward = Transaction(
        block_id= None,
        sender = "0",
        recipient = node_identifier,
        amount = 1,
        signature = None,
    )
    session.add(reward)
    await session.commit()
    await session.refresh(reward)


    hash_block = {
        "transactions": {
            "sender":
        }
    }
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    #Rewareded one coin for mining and sender is 0 which basically the mine itself
    new_block = Block(
        proof=proof,
        previous_hash=previous_hash,
    )
    session.add(new_block)
    await session.commit()
    await session.refresh(new_block)

    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
        signature=None
    )


    response = {
        'message': 'New Block Forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return JSONResponse(response, status_code=200)

@app.post('/new_transaction')
async def new_transaction(request : Request):
    data = await request.json()
    #Check that the required values are present in the POST'ed Data
    required = ['sender', 'recipient', 'amount']
    if not all (k in data for k in required):
        raise HTTPException(status_code=400,detail="Missing values")

    new_transaction = {
        'sender': data['sender'],
        'recipient': data['recipient'],
        'amount': data['amount'],
    }
    signature = data['signature']

    if not blockchain.verify_transaction(data['sender'], new_transaction, signature):
        raise HTTPException(status_code=400, detail="Invalid transaction")

    index = blockchain.new_transaction(
        data['sender'],
        data['recipient'],
        data['amount'],
        signature,
    )
    response = {"Message": f"Transaction added to Blockchain {index}"}

    return JSONResponse(response, status_code=200)

@app.get('/chain')
async def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return JSONResponse(response, status_code=200)

@app.post('/nodes/register')
async def register_nodes(request):
    values = await request.json()

    nodes = values.get('nodes')
    if nodes is None:
        return JSONResponse("Error: Please supply a valid list of nodes", status_code=400)

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }

    return JSONResponse(response, status_code=200)

@app.post('/nodes/resolve')
async def resolve():
    replaced = await blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Longest Chain Updated',
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'message': 'No Longest Chain Available',
            'chain': blockchain.chain,
        }

    return JSONResponse(response, status_code=200)

@app.get('/wallet/details/')
async def wallet(session : AsyncSession = Depends(get_async_session),):
    if node_identifier is None:
        return JSONResponse(
            content={"status" : "error", "message": "Wallet not found"},
        )

    wallet = await session.get(Wallet, node_identifier)

    if wallet is None:
        return JSONResponse(
            content={"status" : "error", "message": "Wallet not found"},
        )

    result = await session.execute(select(Transaction).where(Transaction.sender == node_identifier,
                Transaction.recipient == node_identifier))

    transactions = [{
        "id" : t.id,
        "block_id" : t.block_id,
        "sender": t.sender,
        "recipient" : t.recipient,
        "amount" : t.amount,
        "signatur": t.signature,

    } for t in result.scalars().all()
    ]

    response = {
        "publicKey": node_identifier,
        "balance": wallet.balance,
        "transactions": transactions,
    }

    return JSONResponse(content = {"status":"success", "data":response}, status_code=200)


@app.get('/')
async def root():
    return {'message': 'Welcome to Blockchain!'}



if __name__ == '__main__':
   import uvicorn
   uvicorn.run(app, host='0.0.0.0', port=5002)