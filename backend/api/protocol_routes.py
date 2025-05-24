from fastapi import APIRouter, HTTPException
from protocols.uniswap.router import UniswapV3Router
from web3 import Web3

router = APIRouter()
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_KEY"))

@router.get("/uniswap/route")
async def get_swap_route(
    token_in: str, 
    token_out: str,
    amount: int
):
    router = UniswapV3Router(w3, "0xE592427A0AEce92De3Edee1F18E0157C05861564")
    try:
        return router.find_optimal_route(token_in, token_out, amount)
    except Exception as e:
        raise HTTPException(400, str(e))
