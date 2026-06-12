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

export type IssueDetail = IssueListItem & {
  markdown: string;
  html: string;
  markdown_path: string;
  delivery_preview?: DeliveryPreview | null;
};
