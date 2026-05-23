---
name: briefing
display_name: 高管简报
description: 精简的高管简报风格，页数少、重点突出、一页一主题，适合向管理层汇报
version: "1.0"
tags: [简报, 汇报, 高管, 精简]
style_override: executive_brief
color_scheme_override:
  primary: "#2c3e50"
  secondary: "#7f8c8d"
  accent: "#e74c3c"
  background: "#ffffff"
target_pages_override: 6
layout_preferences:
  prefer_layouts: [cover, text_only, text_image]
analyzer_instructions: 提取最核心的要点和数据，忽略次要细节，每个主题压缩为一段话
designer_instructions: 每页只放一个主题，使用大标题和少量正文，留白充足，强调视觉冲击力
fidelity_threshold: 0.85
---
