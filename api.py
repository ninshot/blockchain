"""
This file contains the api endpoints build using REST through Fastapi

"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from blockchain import BlockChain
#Intiation of our Node
app = FastAPI()

#Intiation of blockchain
blockchain = BlockChain()

private_key, node_identifier = blockchain.create_wallets()
print("This is the wallet publci key:\n", node_identifier)


#endpoints
@app.get("/mine")
async def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    #Rewareded one coin for mining and sender is 0 which basically the mine itself
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
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
async def new_transaction(request):
    data = await request.json
    #Check that the required values are present in the POST'ed Data
    required = ['sender', 'recipient', 'amount']
    if not all (k in data for k in required):
        return JSONResponse("Missing Values",status_code=400)

    #Creation of new transaction
    index = blockchain.new_transaction(data['sender'], data['recipient'], data['amount'])

    response = {'message': f'Transaction will be added to block {index}'}

    return JSONResponse(response, status_code=200)

@app.get('/chain')
async def full_chain(request):
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
    replaced = blockchain.resolve_conflicts()
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

@app.get('/')
async def root():
    return {'message': 'Welcome to Blockchain!'}

if __name__ == '__main__':
   import uvicorn
   uvicorn.run(app, host='0.0.0.0', port=5001)