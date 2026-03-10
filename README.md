# witb (where in the bible?)

Setup
```bash
git clone https://github.com/wakrson/witb
cd witb
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
```

Usage
```bash
# Parse Bible
python -m witb.parse --data=/path/to/pdf
```
