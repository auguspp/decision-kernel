from pathlib import Path

path = Path('tests/test_stock_reading_calendar.py')
text = path.read_text(encoding='utf-8')
old = "SATURDAY = datetime(2026,9,5,10,tzinfo=stock.SHANGHAI_TZ)"
new = "SATURDAY = datetime(2026,9,12,10,tzinfo=stock.SHANGHAI_TZ)"
if text.count(old) != 1:
    raise SystemExit(f'exact fixture replacement count differs: {text.count(old)}')
path.write_text(text.replace(old, new), encoding='utf-8')
print('non-session fixture moved after association cutoff')
