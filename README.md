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
python -m backend.parse --data=/path/to/bible.pdf
```

**Build FAISS index**
```bash
python -m backend.create_database --input=/path/to/verses.csv --output=/path/to/index --window=1
```

**Startup server**
```bash
gunicorn --workers 1 --threads 4 --bind 0.0.0.0:5000 backend.server:app
```

**Start server**
```bash
python -m backend.server
```