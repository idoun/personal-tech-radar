export type IssueListItem = {
  id: number;
  slug: string;
  title: string;
  summary: string;
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
};
