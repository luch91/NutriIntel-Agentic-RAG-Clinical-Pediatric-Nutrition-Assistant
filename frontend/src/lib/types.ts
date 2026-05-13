// TypeScript types mirroring CPNAResponse contract shapes from Prompt 8.
// No `any` types. Discriminated union on query_type.

export interface EvidenceItem {
  source_title: string;
  excerpt_safe: string;
}

export interface EvidenceSummary {
  used_sources: EvidenceItem[];
  retrieval_note: string;
}

export interface NutrientTargetRow {
  nutrient: string;
  value: number;
  unit: string;
  clinical_note: string | null;
}

export interface NutrientPreviewRow {
  nutrient: string;
  rda: number | null;
  ai: number | null;
  unit: string;
}

export interface DrugNutrientDisplay {
  drug: string;
  nutrient: string;
  severity: string;
  note: string;
}

export interface FoodSourceSection {
  nutrient: string;
  foods: string[];
}

export interface MealEntry {
  meal_name: string;
  foods: string[];
  estimated_nutrients: Record<string, number>;
}

export interface DayPlan {
  day: number;
  meals: MealEntry[];
}

export interface MealPlanDisplay {
  days: DayPlan[];
}

export interface QuantitativeMatrix {
  headers: string[];
  rows: Record<string, unknown>[];
}

export interface QualitativePoints {
  entity_a: string;
  points_a: string[];
  entity_b: string;
  points_b: string[];
}

// ---------------------------------------------------------------------------
// Top-level response types — discriminated union on query_type
// ---------------------------------------------------------------------------

export interface TherapyResponse {
  query_type: "therapy";
  title: string;
  summary: string;
  patient_summary: string;
  assumptions_used: string[];
  nutrient_targets: NutrientTargetRow[];
  drug_nutrient_notes: DrugNutrientDisplay[];
  food_sources: FoodSourceSection[];
  meal_plan: MealPlanDisplay | null;
  follow_up_hint: string;
  evidence_summary: EvidenceSummary;
  next_step: string;
}

export interface RecommendationResponse {
  query_type: "recommendation";
  title: string;
  summary: string;
  context_summary: string;
  nutrient_preview: NutrientPreviewRow[] | null;
  practical_guidance: string;
  foods_to_emphasize: string[];
  foods_to_limit: string[];
  therapy_upgrade_note: string | null;
  follow_up_hint: string;
  evidence_summary: EvidenceSummary;
}

export interface ComparisonResponse {
  query_type: "comparison";
  title: string;
  summary: string;
  entities: string[];
  context_or_assumptions: string | null;
  executive_takeaway: string;
  comparison_mode: "quantitative" | "qualitative";
  matrix_or_points: QuantitativeMatrix | QualitativePoints;
  interpretation: string;
  decision_rules: string[];
  follow_up_hint: string;
  evidence_summary: EvidenceSummary;
}

export interface GeneralResponse {
  query_type: "general";
  title: string;
  summary: string;
  direct_answer: string;
  explanation: string;
  examples: string[] | null;
  transition_note: string | null;
  follow_up_hint: string;
  evidence_summary: EvidenceSummary;
}

export type CPNAResponse =
  | TherapyResponse
  | RecommendationResponse
  | ComparisonResponse
  | GeneralResponse;

// ---------------------------------------------------------------------------
// Chat hook types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string | CPNAResponse;
}
