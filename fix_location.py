p = r'C:\Users\tasayur\Desktop\buildee_app\templates\stepmap.html'
with open(p, encoding='utf-8') as f:
    txt = f.read()

old = "location:document.getElementById('sch_location').value,"
new = "location:(()=>{const fl=document.getElementById('sch_location_floor').value;const lo=document.getElementById('sch_location').value.trim();return fl&&lo?fl+' '+lo:fl||lo;})(),"

if old in txt:
    txt = txt.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(txt)
    print('OK: replaced')
else:
    print('ERROR: old string not found')
