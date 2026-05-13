"""
Synthetic EnrichedPassage fixtures for E2E tests.
10 passages covering key clinical topics used across query types.
"""

from app.retrieval import EnrichedPassage

PASSAGES = [
    EnrichedPassage(
        passage_id="shaw2020_ch11_chunk0",
        text=(
            "Type 1 diabetes in children requires careful carbohydrate counting and insulin "
            "dose adjustment. Blood glucose targets: fasting 4–7 mmol/L, post-prandial <10 mmol/L. "
            "Dietary fibre and low-GI foods improve glycaemic control."
        ),
        source_title="Clinical Paediatric Dietetics (Shaw 2020)",
        source_type="shaw_2020",
        condition_tags=["t1d"],
    ),
    EnrichedPassage(
        passage_id="shaw2020_ch12_chunk0",
        text=(
            "Cystic fibrosis (CF) is associated with malabsorption due to exocrine pancreatic "
            "insufficiency. Energy requirements are 110–200% of the estimated average requirement. "
            "Fat-soluble vitamin supplements (A, D, E, K) are mandatory."
        ),
        source_title="Clinical Paediatric Dietetics (Shaw 2020)",
        source_type="shaw_2020",
        condition_tags=["cystic_fibrosis"],
    ),
    EnrichedPassage(
        passage_id="shaw2020_ch12_chunk1",
        text=(
            "Pancreatic enzyme replacement therapy (PERT) such as Creon must be taken with every "
            "meal and snack. Enzyme dose is adjusted according to fat content of food. "
            "Monitoring fat-soluble vitamins A, D, E, K annually is recommended."
        ),
        source_title="Clinical Paediatric Dietetics (Shaw 2020)",
        source_type="shaw_2020",
        condition_tags=["cystic_fibrosis"],
    ),
    EnrichedPassage(
        passage_id="preterm2013_ch2_chunk0",
        text=(
            "Preterm infants have high protein requirements of 3.5–4.5 g/kg/day in the first weeks. "
            "Early enteral nutrition with breast milk is preferred. Fortification with human milk "
            "fortifier provides additional energy, protein, calcium, and phosphorus."
        ),
        source_title="Nutrition of the Preterm Infant (2013)",
        source_type="preterm_2013",
        condition_tags=["preterm"],
    ),
    EnrichedPassage(
        passage_id="dri2006_vitamind_chunk0",
        text=(
            "Vitamin D plays a critical role in calcium absorption, bone mineralisation, immune "
            "function, and cell growth regulation in children. The RDA for children aged 1–18 years "
            "is 600 IU/day. Deficiency leads to rickets and increased susceptibility to infection."
        ),
        source_title="Dietary Reference Intakes (DRI 2006)",
        source_type="dri",
        condition_tags=[],
    ),
    EnrichedPassage(
        passage_id="westafricafct_bambara_chunk0",
        text=(
            "Bambara nut (Vigna subterranea) is a legume widely consumed in West Africa. "
            "Per 100g: protein 18g, fat 6g, carbohydrate 60g, iron 3mg, zinc 3.2mg. "
            "It is drought-tolerant and locally available throughout sub-Saharan Africa."
        ),
        source_title="West Africa Food Composition Table (2019)",
        source_type="west_africa_fct_2019",
        condition_tags=[],
    ),
    EnrichedPassage(
        passage_id="westafricafct_groundnut_chunk0",
        text=(
            "Groundnut (Arachis hypogaea) is a high-protein legume and important food crop in "
            "West Africa. Per 100g: protein 26g, fat 49g, carbohydrate 16g, iron 4.6mg, zinc 3.3mg. "
            "Rich in niacin and folate; good source of unsaturated fatty acids."
        ),
        source_title="West Africa Food Composition Table (2019)",
        source_type="west_africa_fct_2019",
        condition_tags=[],
    ),
    EnrichedPassage(
        passage_id="westafricafct_rice_chunk0",
        text=(
            "Brown rice retains its bran layer and is richer in fibre, B vitamins, and minerals "
            "than white rice. Per 100g cooked: energy 111 kcal, protein 2.6g, fibre 1.8g, "
            "iron 0.5mg. White rice has a higher glycaemic index (GI ~72 vs ~50 for brown rice)."
        ),
        source_title="West Africa Food Composition Table (2019)",
        source_type="west_africa_fct_2019",
        condition_tags=[],
    ),
    EnrichedPassage(
        passage_id="oxford2012_ch22_chunk0",
        text=(
            "Insulin management in type 1 diabetes should be tailored to carbohydrate intake. "
            "Basal-bolus regimens provide flexibility. Carbohydrate counting using insulin-to-carb "
            "ratios (ICR) is recommended for children on multiple daily injections."
        ),
        source_title="Oxford Handbook of Nutrition and Dietetics (2012)",
        source_type="oxford_handbook",
        condition_tags=["t1d"],
    ),
    EnrichedPassage(
        passage_id="drugnutrient2024_creon_chunk0",
        text=(
            "Creon (pancrelipase) is used in cystic fibrosis and other conditions causing "
            "exocrine pancreatic insufficiency. It enhances fat absorption and can improve "
            "fat-soluble vitamin status. Dose: typically 500–4000 lipase units/g dietary fat. "
            "Monitor for fibrosing colonopathy at high doses."
        ),
        source_title="Drug-Nutrient Interactions Handbook (2024)",
        source_type="drug_nutrient",
        condition_tags=["cystic_fibrosis"],
    ),
]
