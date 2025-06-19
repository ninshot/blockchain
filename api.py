"""
This file contains the api endpoints build using REST through Fastapi

"""
from fastapi import FastAPI,HTTPException
from fastapi.responses import JSONResponse
from blockchain import BlockChain
#Intiation of our Node
app = FastAPI()

#Intiation of blockchain
blockchain = BlockChain()

node_identifier, private_key = blockchain.create_wallets()
print("This is the wallet pubic key:\n", node_identifier)
wallets = list(blockchain.get_wallets().keys())[0]


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
async def new_transaction(request):
    data = await request.json
    #Check that the required values are present in the POST'ed Data
    required = ['sender', 'recipient', 'amount']
    if not all (k in data for k in required):
        return JSONResponse(content={"error" : "Missing Values"},status_code=400)

    new_transaction = {
        'sender': data['sender'],
        'recipient': data['recipient'],
        'amount': data['amount'],
    }

    if not blockchain.verify_transaction(data['sender'], new_transaction, data['signature']):
        return JSONResponse(content={"error":"Invalid Transaction"},status_code=400)

    index = blockchain.new_transaction({
        'sender': data['sender'],
        'recipient': data['recipient'],
        'amount': data['amount'],
        'signature': data['signature']
    })
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

@app.get('/wallet')
async def wallet():

    wallets = blockchain.get_wallets()


    for i in wallets.keys():

        if i == node_identifier:
            balance = wallets[i]['balance']
            transactions = wallets[i]['transactions']
            response = {"balance": balance,
                        "transactions": transactions}

            return JSONResponse(response, status_code=200)

@app.get('/')
async def root():
    return {'message': 'Welcome to Blockchain!'}


if __name__ == '__main__':
   import uvicorn
   uvicorn.run(app, host='0.0.0.0', port=5002)