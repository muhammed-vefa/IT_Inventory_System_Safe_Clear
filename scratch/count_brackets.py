
with open('frontend/UI_controller.js', 'r', encoding='utf-8') as f:
    s = f.read()
print(f'Braces: {s.count("{")} / {s.count("}")}')
print(f'Parens: {s.count("(")} / {s.count(")")}')
print(f'Brackets: {s.count("[")} / {s.count("]")}')
