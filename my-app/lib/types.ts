export type Run = {
  text: string;
  font: string;
  size_pt: number;
  color_hex: string;
  bold: boolean;
  italic: boolean;
};

export type ParagraphBlock = {
  id: string;
  type: "paragraph" | "split_row";
  page?: number;
  runs: Run[];
};

export type DividerBlock = {
  id: string;
  type: "divider";
  width_pt: number;
  color_hex: string;
};

export type Block = ParagraphBlock | DividerBlock;

export type Resume = {
  id: string;
  document: {
    source_file: string;
    page_count: number;
    page_size_pt: { width: number; height: number };
    margins_pt?: { left: number; right: number; top: number; bottom: number };
  };
  blocks: Block[];
};
