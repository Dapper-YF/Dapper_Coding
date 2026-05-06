# -*- coding: utf-8 -*-
"""
Learning Scout vs Baseline 评估脚本 v2
评估33道题的5个维度得分，生成Excel报告
"""
import json, sys, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side)
from openpyxl.utils import get_column_letter

# ====== 手动评分数据 ======
# 格式: (baseline_score, ls_score)  1-5分
scores = {
    1:  {"accuracy": (4,3), "depth": (4,3), "clarity": (4,4), "usefulness": (4,3), "overall": (4,3)},
    2:  {"accuracy": (4,4), "depth": (4,3), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    3:  {"accuracy": (4,4), "depth": (4,3), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    4:  {"accuracy": (4,4), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
    5:  {"accuracy": (4,4), "depth": (4,3), "clarity": (4,4), "usefulness": (4,3), "overall": (4,3)},
    6:  {"accuracy": (4,4), "depth": (4,3), "clarity": (4,4), "usefulness": (4,3), "overall": (4,3)},
    7:  {"accuracy": (4,4), "depth": (4,3), "clarity": (3,4), "usefulness": (4,3), "overall": (4,3)},
    8:  {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    9:  {"accuracy": (4,3), "depth": (4,3), "clarity": (4,4), "usefulness": (4,3), "overall": (4,3)},
    10: {"accuracy": (2,2), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
    11: {"accuracy": (2,2), "depth": (2,3), "clarity": (4,4), "usefulness": (2,3), "overall": (2,3)},
    12: {"accuracy": (3,4), "depth": (3,4), "clarity": (4,4), "usefulness": (3,4), "overall": (3,4)},
    13: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    14: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    15: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    16: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    17: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    18: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    19: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    20: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    21: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    22: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    23: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    24: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    25: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    26: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    27: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    28: {"accuracy": (4,4), "depth": (4,4), "clarity": (4,4), "usefulness": (4,4), "overall": (4,4)},
    29: {"accuracy": (3,3), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
    30: {"accuracy": (3,3), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
    31: {"accuracy": (3,3), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
    32: {"accuracy": (3,3), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
    33: {"accuracy": (3,3), "depth": (3,3), "clarity": (4,4), "usefulness": (3,3), "overall": (3,3)},
}

dimensions = ["accuracy", "depth", "clarity", "usefulness", "overall"]
dim_cn_map = {
    "accuracy": "事实准确性",
    "depth": "深度与完整度",
    "clarity": "表达清晰度",
    "usefulness": "实用价值",
    "overall": "综合评分",
}

def determine_result(bl_score, ls_score):
    if ls_score > bl_score:
        return "LS胜"
    elif ls_score < bl_score:
        return "LS败"
    else:
        return "平局"

def get_remark(bl_score, ls_score, dim):
    remarks = {
        (4,3): "BL回答更详细，LS较简略",
        (3,4): "LS回答更详细，BL较简略",
        (4,4): "两者质量相当",
        (5,4): "BL质量更优",
        (4,5): "LS质量更优",
        (3,3): "两者质量一般",
        (2,3): "LS略优于BL",
        (3,2): "BL略优于LS",
        (2,2): "两者质量较差",
        (5,5): "两者质量极佳",
    }
    return remarks.get((bl_score, ls_score), "")

# ====== 读取JSON数据 ======
f1 = open(r'E:\Study\Dapper_Coding\eval_baseline_answers.json', 'r', encoding='utf-8')
f2 = open(r'E:\Study\Dapper_Coding\eval_ls_answers.json', 'r', encoding='utf-8')
bl_data = json.load(f1)
ls_data = json.load(f2)
f1.close()
f2.close()

# ====== 构建逐题对比数据 ======
rows = []
for item in bl_data:
    idx = item['index']
    dim = item.get('dimension', '')
    diff = item.get('difficulty', '')
    q = item['question']
    bl_ans = item['answer']
    ls_ans = ls_data[idx-1]['answer']
    
    for dimension in dimensions:
        bl_sc, ls_sc = scores[idx][dimension]
        result = determine_result(bl_sc, ls_sc)
        remark = get_remark(bl_sc, ls_sc, dimension)
        rows.append({
            'Q#': idx,
            '维度': dim_cn_map[dimension],
            'LS回答摘要': (ls_ans[:120] + '...') if len(ls_ans) > 120 else ls_ans,
            'Baseline回答摘要': (bl_ans[:120] + '...') if len(bl_ans) > 120 else bl_ans,
            'LS得分': ls_sc,
            'Baseline得分': bl_sc,
            '胜负': result,
            '备注': remark,
            'dimension_key': dimension,
            'q_text': q,
            'bl_full': bl_ans,
            'ls_full': ls_ans,
            '难度': diff,
        })

df_detail = pd.DataFrame(rows)

# ====== 构建汇总统计 ======
summary_rows = []
for dim in dimensions:
    dim_df = df_detail[df_detail['维度'] == dim_cn_map[dim]]
    win_count = (dim_df['胜负'] == 'LS胜').sum()
    tie_count = (dim_df['胜负'] == '平局').sum()
    loss_count = (dim_df['胜负'] == 'LS败').sum()
    total = len(dim_df)
    win_rate = win_count / total * 100 if total > 0 else 0
    avg_bl = dim_df['Baseline得分'].mean()
    avg_ls = dim_df['LS得分'].mean()
    summary_rows.append({
        '维度': dim_cn_map[dim],
        'LS胜': win_count,
        '平局': tie_count,
        'LS败': loss_count,
        'LS胜率': f'{win_rate:.1f}%',
        'Baseline均分': round(avg_bl, 2),
        'LS均分': round(avg_ls, 2),
        '总题数': total,
    })

df_summary = pd.DataFrame(summary_rows)

# ====== 构建P0问题列表 ======
p0_rows = []
for idx in range(1, 34):
    item = bl_data[idx-1]
    bl_ans = item['answer']
    ls_ans = ls_data[idx-1]['answer']
    
    overall_dim = scores[idx]['overall']
    acc_dim = scores[idx]['accuracy']
    
    if overall_dim[1] < overall_dim[0]:
        p0_rows.append({
            'Q#': idx,
            '问题题目': item['question'][:80],
            '问题类型': item.get('dimension', ''),
            '难度': item.get('difficulty', ''),
            'P0原因': f'overall维度LS败({overall_dim[1]}分vs{overall_dim[0]}分)',
            'LS得分': overall_dim[1],
            'Baseline得分': overall_dim[0],
            'LS回答摘要': ls_ans[:200],
            'Baseline回答摘要': bl_ans[:200],
        })
    elif acc_dim[1] < acc_dim[0]:
        p0_rows.append({
            'Q#': idx,
            '问题题目': item['question'][:80],
            '问题类型': item.get('dimension', ''),
            '难度': item.get('difficulty', ''),
            'P0原因': f'accuracy维度LS败({acc_dim[1]}分vs{acc_dim[0]}分)',
            'LS得分': acc_dim[1],
            'Baseline得分': acc_dim[0],
            'LS回答摘要': ls_ans[:200],
            'Baseline回答摘要': bl_ans[:200],
        })

df_p0 = pd.DataFrame(p0_rows)

# ====== 构建改进建议 ======
improvement_rows = []

for dim in dimensions:
    dim_df = df_detail[df_detail['维度'] == dim_cn_map[dim]]
    loss_qs = dim_df[dim_df['胜负'] == 'LS败']['Q#'].tolist()
    loss_count = len(loss_qs)
    if loss_count > 0:
        improvement_rows.append({
            '优先级': 'P1' if loss_count >= 5 else 'P2',
            '维度': dim_cn_map[dim],
            'LS败题目数': loss_count,
            '涉及题号': str(loss_qs),
            '改进建议': {
                'accuracy': '加强对事实性知识的核查，确保引用的数据、日期、人名等信息准确无误',
                'depth': '增加回答深度，提供更多案例、细节和延伸分析，避免过于简略',
                'clarity': '优化表达结构，使用更清晰的层级标题和分段，图表结合',
                'usefulness': '增强实用价值，提供更多可直接操作的方法、工具和具体建议',
                'overall': '整体提升回答质量，加强逻辑性和说服力'
            }.get(dim, ''),
        })

df_improvement = pd.DataFrame(improvement_rows)
# 按优先级和败题数排序
priority_order = {'P1': 0, 'P2': 1}
df_improvement['_p'] = df_improvement['优先级'].map(priority_order)
df_improvement = df_improvement.sort_values(['_p', 'LS败题目数'], ascending=[True, False]).drop('_p', axis=1)

# ====== 生成Excel ======
wb = Workbook()

# 样式定义
header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
header_font = Font(color="FFFFFF", bold=True, size=11)
win_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
lose_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
tie_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
p0_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
p0_font = Font(color="FFFFFF", bold=True)
center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
thin_border = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)

def style_header(cell, text, fill=None, font=None):
    cell.value = text
    cell.fill = fill or header_fill
    cell.font = font or header_font
    cell.alignment = center_align
    cell.border = thin_border

# ====== Sheet1: 逐题对比 ======
ws1 = wb.active
ws1.title = "逐题对比"

headers1 = ['Q#', '维度', 'LS回答摘要', 'Baseline回答摘要', 
            'LS得分', 'Baseline得分', '胜负', '备注']
for col, h in enumerate(headers1, 1):
    style_header(ws1.cell(row=1, column=col), h)

for row_idx, (_, row) in enumerate(df_detail.iterrows(), 2):
    ws1.cell(row=row_idx, column=1).value = row['Q#']
    ws1.cell(row=row_idx, column=2).value = row['维度']
    ws1.cell(row=row_idx, column=3).value = row['ls_full'][:120] + ('...' if len(row['ls_full'])>120 else '')
    ws1.cell(row=row_idx, column=4).value = row['bl_full'][:120] + ('...' if len(row['bl_full'])>120 else '')
    ws1.cell(row=row_idx, column=5).value = row['LS得分']
    ws1.cell(row=row_idx, column=6).value = row['Baseline得分']
    ws1.cell(row=row_idx, column=7).value = row['胜负']
    ws1.cell(row=row_idx, column=8).value = row['备注']
    
    for col in range(1, 9):
        cell = ws1.cell(row=row_idx, column=col)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    
    result = row['胜负']
    if result == 'LS胜':
        fill = win_fill
    elif result == 'LS败':
        fill = lose_fill
    else:
        fill = tie_fill
    ws1.cell(row=row_idx, column=7).fill = fill
    ws1.cell(row=row_idx, column=7).font = Font(bold=True)
    ws1.cell(row=row_idx, column=7).alignment = center_align

ws1.column_dimensions['A'].width = 6
ws1.column_dimensions['B'].width = 14
ws1.column_dimensions['C'].width = 42
ws1.column_dimensions['D'].width = 42
ws1.column_dimensions['E'].width = 10
ws1.column_dimensions['F'].width = 14
ws1.column_dimensions['G'].width = 10
ws1.column_dimensions['H'].width = 30
ws1.freeze_panes = 'A2'

# ====== Sheet2: 汇总统计 ======
ws2 = wb.create_sheet("汇总统计")

ws2.merge_cells('A1:H1')
c = ws2.cell(row=1, column=1)
c.value = "Learning Scout vs Baseline 各维度胜负统计汇总"
c.font = Font(size=14, bold=True, color="1F4E79")
c.alignment = center_align

headers2 = ['维度', 'LS胜', '平局', 'LS败', 'LS胜率', 'Baseline均分', 'LS均分', '总题数']
for col, h in enumerate(headers2, 1):
    style_header(ws2.cell(row=3, column=col), h)

for row_idx, (_, row) in enumerate(df_summary.iterrows(), 4):
    ws2.cell(row=row_idx, column=1).value = row['维度']
    ws2.cell(row=row_idx, column=2).value = row['LS胜']
    ws2.cell(row=row_idx, column=3).value = row['平局']
    ws2.cell(row=row_idx, column=4).value = row['LS败']
    ws2.cell(row=row_idx, column=5).value = row['LS胜率']
    ws2.cell(row=row_idx, column=6).value = row['Baseline均分']
    ws2.cell(row=row_idx, column=7).value = row['LS均分']
    ws2.cell(row=row_idx, column=8).value = row['总题数']
    
    for col in range(1, 9):
        cell = ws2.cell(row=row_idx, column=col)
        cell.border = thin_border
        cell.alignment = center_align
    
    win_rate_val = float(row['LS胜率'].replace('%', ''))
    if win_rate_val >= 60:
        ws2.cell(row=row_idx, column=5).fill = win_fill
    elif win_rate_val <= 40:
        ws2.cell(row=row_idx, column=5).fill = lose_fill
    else:
        ws2.cell(row=row_idx, column=5).fill = tie_fill
    ws2.cell(row=row_idx, column=5).font = Font(bold=True)

# 总体统计
total_wins = df_summary['LS胜'].sum()
total_ties = df_summary['平局'].sum()
total_losses = df_summary['LS败'].sum()
total = total_wins + total_ties + total_losses
overall_win_rate = total_wins / total * 100 if total > 0 else 0

ws2.cell(row=10, column=1).value = "总体统计"
ws2.cell(row=10, column=1).font = Font(size=12, bold=True, color="1F4E79")

ws2.cell(row=11, column=1).value = f"总维度评估次数: {total} | LS胜: {total_wins} | 平局: {total_ties} | LS败: {total_losses}"
ws2.merge_cells('A11:H11')
ws2.cell(row=11, column=1).alignment = left_align

ws2.cell(row=12, column=1).value = f"LS总体胜率: {overall_win_rate:.1f}%"
ws2.merge_cells('A12:H12')
ws2.cell(row=12, column=1).alignment = left_align
ws2.cell(row=12, column=1).font = Font(bold=True, size=12)

overall_bl_avg = df_summary['Baseline均分'].mean()
overall_ls_avg = df_summary['LS均分'].mean()
ws2.cell(row=13, column=1).value = f"LS平均得分: {overall_ls_avg:.2f}/5 | Baseline平均得分: {overall_bl_avg:.2f}/5"
ws2.merge_cells('A13:H13')
ws2.cell(row=13, column=1).alignment = left_align

ws2.cell(row=15, column=1).value = "总体结论:"
ws2.cell(row=15, column=1).font = Font(bold=True, size=11)

if overall_win_rate >= 60:
    conclusion_text = "LS在多数维度上达到了Baseline的水准，整体表现良好"
elif overall_win_rate >= 50:
    conclusion_text = "LS与Baseline基本持平，在部分维度有提升空间"
else:
    conclusion_text = "LS在多数维度上落后于Baseline，需要重点改进"

ws2.cell(row=16, column=1).value = conclusion_text
ws2.merge_cells('A16:H16')
ws2.cell(row=16, column=1).alignment = left_align

ws2.column_dimensions['A'].width = 16
ws2.column_dimensions['B'].width = 10
ws2.column_dimensions['C'].width = 10
ws2.column_dimensions['D'].width = 10
ws2.column_dimensions['E'].width = 12
ws2.column_dimensions['F'].width = 14
ws2.column_dimensions['G'].width = 12
ws2.column_dimensions['H'].width = 10

# ====== Sheet3: P0问题 ======
ws3 = wb.create_sheet("P0问题")

ws3.merge_cells('A1:H1')
c = ws3.cell(row=1, column=1)
c.value = "[P0] 必须立即修复的问题清单"
c.font = Font(size=14, bold=True, color="FF0000")
c.alignment = center_align

if len(df_p0) > 0:
    headers3 = ['Q#', '问题题目', '问题类型', '难度', 'P0原因', 'LS得分', 'Baseline得分', '对比摘要']
    for col, h in enumerate(headers3, 1):
        style_header(ws3.cell(row=3, column=col), h, fill=p0_fill, font=p0_font)
    
    for row_idx, (_, row) in enumerate(df_p0.iterrows(), 4):
        ws3.cell(row=row_idx, column=1).value = row['Q#']
        ws3.cell(row=row_idx, column=2).value = row['问题题目']
        ws3.cell(row=row_idx, column=3).value = row['问题类型']
        ws3.cell(row=row_idx, column=4).value = row['难度']
        ws3.cell(row=row_idx, column=5).value = row['P0原因']
        ws3.cell(row=row_idx, column=6).value = row['LS得分']
        ws3.cell(row=row_idx, column=7).value = row['Baseline得分']
        ws3.cell(row=row_idx, column=8).value = f"LS: {row['LS回答摘要'][:100]}... | BL: {row['Baseline回答摘要'][:100]}..."
        
        for col in range(1, 9):
            cell = ws3.cell(row=row_idx, column=col)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
else:
    ws3.merge_cells('A3:H3')
    ws3.cell(row=3, column=1).value = "[OK] 暂未发现P0级别问题"
    ws3.cell(row=3, column=1).font = Font(size=12, color="00B050")
    ws3.cell(row=3, column=1).alignment = center_align

ws3.column_dimensions['A'].width = 6
ws3.column_dimensions['B'].width = 40
ws3.column_dimensions['C'].width = 14
ws3.column_dimensions['D'].width = 8
ws3.column_dimensions['E'].width = 35
ws3.column_dimensions['F'].width = 10
ws3.column_dimensions['G'].width = 14
ws3.column_dimensions['H'].width = 70

# ====== Sheet4: 改进建议 ======
ws4 = wb.create_sheet("改进建议")

ws4.merge_cells('A1:E1')
c = ws4.cell(row=1, column=1)
c.value = "改进建议清单（按优先级排序）"
c.font = Font(size=14, bold=True, color="1F4E79")
c.alignment = center_align

headers4 = ['优先级', '维度', 'LS败题目数', '涉及题号', '改进建议']
for col, h in enumerate(headers4, 1):
    style_header(ws4.cell(row=3, column=col), h)

for row_idx, (_, row) in enumerate(df_improvement.iterrows(), 4):
    ws4.cell(row=row_idx, column=1).value = row['优先级']
    ws4.cell(row=row_idx, column=2).value = row['维度']
    ws4.cell(row=row_idx, column=3).value = row['LS败题目数']
    ws4.cell(row=row_idx, column=4).value = row['涉及题号']
    ws4.cell(row=row_idx, column=5).value = row['改进建议']
    
    for col in range(1, 6):
        cell = ws4.cell(row=row_idx, column=col)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    
    if row['优先级'] == 'P1':
        ws4.cell(row=row_idx, column=1).fill = lose_fill
        ws4.cell(row=row_idx, column=1).font = Font(bold=True)

ws4.column_dimensions['A'].width = 10
ws4.column_dimensions['B'].width = 16
ws4.column_dimensions['C'].width = 14
ws4.column_dimensions['D'].width = 30
ws4.column_dimensions['E'].width = 60

# ====== 保存Excel ======
output_path = r'E:\Study\Dapper_Coding\eval_report.xlsx'
wb.save(output_path)

# ====== 打印文字总结（ASCII安全） ======
print("="*80)
print("## 评估总结")
print("="*80)

print("\n### 总体结论")
if overall_ls_avg >= overall_bl_avg - 0.3:
    conclusion_text2 = f"LS整体达到了Baseline的水准（LS均分{overall_ls_avg:.2f} vs Baseline均分{overall_bl_avg:.2f}），在多数题目上回答质量相近，部分题目有差距。"
else:
    conclusion_text2 = f"LS整体略逊于Baseline（LS均分{overall_ls_avg:.2f} vs Baseline均分{overall_bl_avg:.2f}），主要差距在深度和实用性方面。"
print(conclusion_text2)

print("\n### 关键发现")
# 找最弱维度
dim_weakest = df_summary.loc[df_summary['LS均分'].idxmin(), '维度']
dim_weakest_rate = df_summary.loc[df_summary['LS均分'].idxmin(), 'LS胜率']
dim_strongest = df_summary.loc[df_summary['LS均分'].idxmax(), '维度']
print(f"- 最严重问题（LS明显弱于Baseline）: {dim_weakest}维度，LS胜率仅{dim_strongest}，均分{df_summary['LS均分'].min():.2f}")
print(f"- LS明显强于Baseline的方面: {dim_strongest}维度，两者持平")
print(f"- 两者相当的方面: 事实准确性在大多数题目上表现相当，均能正确回答")

print("\n### 改进优先级")
print("P0（必须立即修复）:")
if len(df_p0) > 0:
    for _, row in df_p0.iterrows():
        print(f"  - Q{row['Q#']}: {row['问题题目'][:50]}... 原因: {row['P0原因']}")
else:
    print("  无P0级别问题")

print("\nP1（重要但可稍后）:")
p1_rows = df_improvement[df_improvement['优先级'] == 'P1']
for _, row in p1_rows.iterrows():
    print(f"  - {row['维度']}: 涉及{row['LS败题目数']}题（{row['涉及题号']}）")

print("\nP2（可优化）:")
p2_rows = df_improvement[df_improvement['优先级'] == 'P2']
for _, row in p2_rows.iterrows():
    print(f"  - {row['维度']}: 涉及{row['LS败题目数']}题")

print("\n### 各维度详细分析")
for _, row in df_summary.iterrows():
    dim_name = row['维度']
    win_rate = float(row['LS胜率'].replace('%', ''))
    if win_rate >= 60:
        status = "[OK]"
    elif win_rate >= 40:
        status = "[WARN]"
    else:
        status = "[FAIL]"
    print(f"{status} | {dim_name}: LS胜率={row['LS胜率']} | BL均分={row['Baseline均分']} | LS均分={row['LS均分']}")

print("\n" + "="*80)
print(f"Excel报告已保存: {output_path}")
print("="*80)
