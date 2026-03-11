# witb (where in the bible)

## Prerequisites
```bash
sudo apt-get update && sudo apt-get install -y g++ gcc build-essential
sudo apt-get install -y python3.12 python3.12-venv
```

## Setup
```bash
git clone https://github.com/wakrson/witb && cd witb
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -e .
pip install flash-attn --no-build-isolation
```

## Usage

**Parse Bible PDF**
```bash
python -m witb.parse --data=/path/to/bible.pdf
```

**Build FAISS index**
```bash
python -m witb.create_database --input=/path/to/verses.csv --output=/path/to/index --window=1
```

**Start server**
```bash
python -m witb.server
```