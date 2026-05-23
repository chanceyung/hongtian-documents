---
name: data-focus
display_name: 数据聚焦
description: 以数据可视化和表格为核心，突出数据卡片和双栏布局，适合包含大量数据的报告
version: "1.0"
tags: [数据, 表格, 图表, 报告]
style_override: business_chart
color_scheme_override:
  primary: "#1a5276"
  secondary: "#2e86c1"
  accent: "#3498db"
  background: "#ffffff"
target_pages_override: 12
layout_preferences:
  prefer_layouts: [data_card, text_table, two_column]
analyzer_instructions: 重点关注数据表格、数值信息和统计指标，将相关数据分组到同一页面
designer_instructions: 优先使用 data_card 布局展示关键数据，表格保持清晰可读，使用蓝色系配色
fidelity_threshold: 0.90
---
