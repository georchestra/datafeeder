=== CONTEXTE ADDITIONNEL DE L'UTILISATEUR (PRIORITÉ ABSOLUE — voir la règle de priorité du system prompt) ===
{extra_context}
=== FIN DU CONTEXTE ADDITIONNEL ===

Generate metadata for the following dataset:
- Dataset title: {title}
- Columns (name and ISO type): {columns_with_types}
- Bounding box (minx miny maxx maxy): {bbox}
- Sample data:
{sample}
- Current abstract:
{current_abstract}
- Current keywords:
{current_keywords}
- Current topics:
{current_topics}
- Available keywords (prioritize these when relevant, complement with free keywords if fewer than 5 match): 
{keywords}
- Available topic categories (prioritize these when relevant): 
{topics}
- Instructions mode
{mode_instruction}
