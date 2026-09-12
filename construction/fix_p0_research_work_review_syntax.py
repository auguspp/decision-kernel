from pathlib import Path

path = Path('src/decision_kernel/runtime/current_state_delivery.py')
text = path.read_text()
line = '        return {"production_configuration": configuration, "production_inputs": packages,\n'
doubled = line + line
assert text.count(doubled) == 1
path.write_text(text.replace(doubled, line, 1))
