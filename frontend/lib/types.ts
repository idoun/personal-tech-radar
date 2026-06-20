export type IssueScore = {
  interest_score: number;
  project_score: number;
  novelty_score: number;
  actionability_score: number;
  credibility_score: number;
  community_score: number;
  final_score: number;
  reason: string;
  recommended_action: string;
};

export type AuthUser = {
  id: number;
  email: string;
  is_active: boolean;
};

export type AuthSession = {
  authenticated: boolean;
  user?: AuthUser | null;
  access_token?: string | null;
  token_type?: string;
};

export type DeliveryDecision = {
  should_send: boolean;
  important: boolean;
  threshold: number;
  important_threshold: number;
  reason: string;
};

export type TelegramPreview = {
  title: string;
  body: string;
};

export type DeliveryPreview = {
  article_slug: string;
  channel: string;
  decision: DeliveryDecision;
  telegram: TelegramPreview;
};

export type IssueListItem = {
  id: number;
  slug: string;
  title: string;
  summary: string;
  short_summary: string;
  impact_summary: string;
  action_items: string[];
  tags: string[];
  radar_category: string;
  radar_status: string;
  score: IssueScore;
  issue_date: string;
  year: number;
  month: number;
  is_published: boolean;
};

export type IssueGroupMonth = {
  year: number;
  month: number;
  label: string;
  items: IssueListItem[];
};

export type IssueSearchResult = IssueListItem & {
  matched_field: string;
  snippet: string;
  matched_terms: string[];
  match_score: number;
};

export type IssueSearchResponse = {
  query: string;
  total: number;
  items: IssueSearchResult[];
};

export type ArticleFavorite = {
  id: number;
  issue_slug: string;
  issue_date: string;
  article_key: string;
  article_title: string;
  article_index: number;
  created_at: string;
};

export type IssueDetail = IssueListItem & {
  markdown: string;
  html: string;
  markdown_path: string;
  community_reaction_summary: string;
  community_reaction_bullets: string[];
  delivery_preview?: DeliveryPreview | null;
};
