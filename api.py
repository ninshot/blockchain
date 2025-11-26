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

    last_block = await blockchain.last_block(session)
    if last_block is None:
        last_proof = 100
        previous_hash = "1"
    else:
        last_proof = last_block['proof']
        previous_hash = last_block['previous_hash']

    proof = blockchain.proof_of_work(last_proof)

    await blockchain.new_transaction(
        session,
        sender="0",
        recipient=node_identifier,
        amount=1,
        signature=None,
    )

    block = await blockchain.new_block(session, proof, previous_hash)

    response = {
        "message": "New Block Forged",
        "index": block['index'],
        "transactions": block['transactions'],
        "proof": block['proof'],
        "previous_hash": block['previous_hash'],
    }

    return JSONResponse(response, status_code=200)

@app.post('/new_transaction')
async def new_transaction(request : Request, session : AsyncSession = Depends(get_async_session)):
    data = await request.json()
    #Check that the required values are present in the POST'ed Data
    required = ['sender', 'recipient', 'amount', 'signature']
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

    try:
        index = await blockchain.new_transaction(
            session,
            sender = data['sender'],
            recipient= data['recipient'],
            amount=data['amount'],
            signature = signature,
    )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


    response = {"Message": f"Transaction added to Blockchain {index}"}

    return JSONResponse(response, status_code=200)

@app.get('/chain')
async def full_chain(session : AsyncSession = Depends(get_async_session)):
    chain = await blockchain.get_chain(session)
    response = {
        'chain': chain,
        'length': len(chain),
    }
    return JSONResponse(response, status_code=200)

@app.post('/nodes/register')
async def register_nodes(request : Request, session : AsyncSession = Depends(get_async_session)):
    values = await request.json()

    nodes = values.get('nodes')
    if nodes is None or not isinstance(nodes, list):
        return JSONResponse("Error: Please supply a valid list of nodes", status_code=400)

    for node in nodes:
        await blockchain.register_node(session,node)

    all_nodes = await blockchain.get_nodes(session)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': all_nodes,
    }

    return JSONResponse(response, status_code=200)

@app.post('/nodes/resolve')
async def resolve(
        session : AsyncSession = Depends(get_async_session),
):
    replaced = await blockchain.resolve_conflicts(session)
    chain = await blockchain.get_chain(session)

    if replaced:
        response = {
            'message': 'Longest Chain Updated',
            'new_chain': chain,
        }
    else:
        response = {
            'message': 'No Longest Chain Available',
            'chain': chain,
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