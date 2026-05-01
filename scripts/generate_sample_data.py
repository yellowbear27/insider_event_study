#!/usr/bin/env python3
"""One-time script to generate realistic sample insider trades for testing."""
import json, random, sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path so config imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import RAW_DIR

def main():
    random.seed(42)
    tickers = ['NVDA', 'CDNS', 'SNPS']
    data = []

    for _ in range(60):
        ticker = random.choice(tickers)
        start = datetime(2018, 1, 1)
        end = datetime(2020, 6, 1)
        rand_day = start + timedelta(days=random.randint(0, (end - start).days))
        filing_date = (rand_day + timedelta(days=random.randint(1, 5))).strftime('%Y-%m-%d')
        
        t_type = random.choices(['Purchase', 'Sale'], weights=[0.4, 0.6])[0]
        initial_shares = random.randint(50, 5000)
        
        if t_type == 'Sale':
            remaining = 0 if random.random() < 0.3 else random.randint(10, max(initial_shares - 10, 20))
        else:
            remaining = initial_shares + random.randint(100, 2000)
            
        data.append({
            'symbol': ticker,
            'transaction_date': rand_day.strftime('%Y-%m-%d'),
            'filing_date': filing_date,
            'type': t_type,
            'shares': remaining,
            'owner_name': f'Senator_{random.randint(100,999)}'
        })

    output_path = RAW_DIR / 'senate_trades.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'✅ Generated {len(data)} sample trades → {output_path}')

if __name__ == '__main__':
    main()
