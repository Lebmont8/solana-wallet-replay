# Solana Wallet Replay

Read a wallet’s SPL token balance changes and replay a fixed-size copy rule without placing orders.

## Run locally

Python 3.11+; no dependencies, service accounts, or network calls are required.

~~~sh
python3 serve.py
~~~

Open http://127.0.0.1:8000. Use `--port 8001` if port 8000 is busy.

Try lowering the buy cap from `3` to `1.50` and replay. The first MOSS buy is skipped, so the later sale cannot use inventory from it.

## How it works

The parser reads the shape of Solana transaction metadata: it adds token accounts belonging to the tracked owner, takes pre/post deltas, and only treats a single non-quote token moving against the USDC fixture mint as a swap. Failed transactions, duplicates, transfers and ambiguous movements are not treated as buys. Entries contain synthetic account identifiers and balances.

This is not a program-specific Solana decoder or an RPC client. It does not infer native SOL swaps, parse arbitrary multi-token routes, or value unsold inventory. The simulated fee in USDC is not the source transaction's Solana network fee. No signer, private keys or funded wallet are needed.

## Check the result

~~~sh
python3 -B -m unittest -v
curl 'http://127.0.0.1:8000/api/replay?budget=75&clip=20&cap=1.50&fee=30'
~~~

`fixture.json` is the input, `demo.py` calculates the result, and `serve.py` serves the browser UI and the same result as JSON.
