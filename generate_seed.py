import json

with open('seed.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

sql = ''
for t_key, t_data in data.items():
    stats_json = json.dumps(t_data['stats']).replace("'", "''")
    tax_json = json.dumps(t_data['tax']).replace("'", "''")
    title = t_data['title'].replace("'", "''")
    desc = t_data['desc'].replace("'", "''")
    meta = t_data['meta'].replace("'", "''")
    
    sql += f"INSERT INTO public.tracks (key, title, desc_text, meta_text, stats, tax, display_order) VALUES ('{t_key}', '{title}', '{desc}', '{meta}', '{stats_json}'::jsonb, '{tax_json}'::jsonb, {t_data.get('display_order', 0)}) ON CONFLICT (key) DO NOTHING;\n"
    
    for p in t_data['problems']:
        p_title = p['title'].replace("'", "''")
        p_detail = p['detail'].replace("'", "''")
        p_context = p['context'].replace("'", "''")
        p_impact = p['impact'].replace("'", "''")
        tags_json = json.dumps(p['tags']).replace("'", "''")
        
        # Seeded problems are pre-approved
        sql += f"INSERT INTO public.problems (problem_key, track_key, title, detail, context, impact, tags, status) VALUES ('{p['problem_key']}', '{t_key}', '{p_title}', '{p_detail}', '{p_context}', '{p_impact}', '{tags_json}'::jsonb, 'approved') ON CONFLICT (problem_key) DO NOTHING;\n"

with open('seed.sql', 'w', encoding='utf-8') as f:
    f.write(sql)
