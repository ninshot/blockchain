"""
This file contains the api endpoints build using REST through Fastapi

"""
import uuid
from uuid import uuid4
from fastapi import FastAPI,HTTPException, Request
from fastapi.responses import JSONResponse
from blockchain import BlockChain
from fastapi.middleware.cors import CORSMiddleware
#Intiation of our Node
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Intiation of blockchain
blockchain = BlockChain()

@app.post("/wallet/create")
async def create_wallet():
    global node_identifier
    public_key, private_key = blockchain.create_wallets()
    node_identifier = public_key
    response = {
        "data" : {
            "publicKey" : public_key,
            "privateKey" : private_key
        }
    }
    return JSONResponse(content={"status" : "success", "data" :response},status_code=200)

@app.get("/mine")
async def mine():
    if node_identifier is None:
        return JSONResponse(
            content={"status" : "Error", "message" : "No Wallet found"}, status_code=400
        )

    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    #Rewareded one coin for mining and sender is 0 which basically the mine itself
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
        signature=None
    )

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
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
async def wallet():

    wallets = blockchain.get_wallets()
    wallet = wallets.get(node_identifier)

    if wallet is None:
        return JSONResponse(
            content={ "status" : "error","message": "Wallet not found"}, status_code=404
        )

    balance = wallet['balance']
    transactions = wallet['transactions']

    response = {
        "publicKey": node_identifier,
        "balance": balance,
        "transactions": transactions
    }

    return JSONResponse(content = {"status":"success", "data":response}, status_code=200)


@app.get('/')
async def root():
    return {'message': 'Welcome to Blockchain!'}



if __name__ == '__main__':
   import uvicorn
   uvicorn.run(app, host='0.0.0.0', port=5002)