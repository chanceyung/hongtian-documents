---
name: academic
display_name: 学术论文
description: 学术论文风格，结构化章节排版，适合研究论文、技术报告、白皮书
version: "1.0"
tags: [学术, 论文, 技术, 白皮书]
style_override: academic_paper
color_scheme_override:
  primary: "#1b4332"
  secondary: "#2d6a4f"
  accent: "#40916c"
  background: "#ffffff"
target_pages_override: 15
layout_preferences:
  prefer_layouts: [text_only, two_column, text_table]
analyzer_instructions: 识别论文章节结构（摘要、引言、方法、结果、讨论），保持学术严谨性，不改变专业术语
designer_instructions: 使用双栏布局，保持学术风格排版，标题层次分明，参考文献独立成页
fidelity_threshold: 0.98
---
