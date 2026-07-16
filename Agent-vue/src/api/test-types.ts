export type TestMode = 'knowledge' | 'fun'
export type AttemptStatus = 'draft' | 'analyzing' | 'completed' | 'failed'

export interface TestOption { id: string; text: string }
export interface TestQuestion { id: string; prompt: string; options: TestOption[] }
export interface PublicQuestionnaire {
  mode: TestMode
  title: string
  description: string
  question_count: 5 | 10 | 15 | 20
  questions: TestQuestion[]
}
export interface AnswerSelection { question_id: string; selected_option_id: string }
export interface AttemptSummary { id: string; status: AttemptStatus; created_at: string; updated_at: string; score?: number | null }
export interface TestSummary { id: string; title: string; description: string; mode: TestMode; question_count: number; updated_at: string }
export interface TestSession extends TestSummary { questionnaire: PublicQuestionnaire; attempts: AttemptSummary[] }
export interface ChartItem { label: string; value: number; max_value: number }
export interface ResultChart { kind: 'radar' | 'bar' | 'donut'; title: string; items: ChartItem[] }
export interface ResultAnalysis { title: string; summary: string; sections?: { heading: string; body: string }[]; mastered?: { heading: string; body: string }[]; weaknesses?: { heading: string; body: string }[]; recommendations?: { heading: string; body: string }[]; charts?: ResultChart[] }
export interface AttemptDetail {
  id: string
  status: AttemptStatus
  mode?: TestMode
  questionnaire: PublicQuestionnaire
  answers: AnswerSelection[]
  error_message?: string
  result?: {
    score?: number
    max_score?: number
    correct_count?: number
    question_count?: number
    questions?: Array<TestQuestion & { selected_option_id: string; correct_option_id: string; is_correct: boolean; explanation: string }>
    analysis: ResultAnalysis
  }
}
export interface TestPreferences { user_id: string; generation_provider_id?: string | null; generation_model?: string | null; analysis_provider_id?: string | null; analysis_model?: string | null }
export interface TestList { items: TestSummary[]; next_cursor?: string | null }
export interface GenerationState { state: 'generating' | 'completed' | 'failed'; request_id: string; test_id?: string | null; error_message?: string | null; retry_after_ms?: number }
