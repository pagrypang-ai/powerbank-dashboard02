import streamlit as st
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import factor_cmap
from bokeh.palettes import Category20
import re

st.set_page_config(page_title="Power Bank Dashboard", layout="wide")
st.title("🔋 充电宝对比可视化看板")

@st.cache_data(ttl=600)
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1fkMRXkdKVdYFN3d_Y7bhFtA1BGIUlA3xAG86UvvhT1w/export?format=csv&gid=0"
    df = pd.read_csv(sheet_url)
    
    # 确保 Price 是数字
    if 'Price' in df.columns:
        df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
    
    df = df.dropna(subset=['Price', 'Capacity/mAh'])
    df = df.fillna('')
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"数据读取失败: {e}")
    st.stop()

st.sidebar.header("⚙️ 选项")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

if 'Brand' in df.columns:
    all_brands = sorted(df['Brand'].unique().tolist())
    selected_brands = st.sidebar.multiselect("筛选品牌", options=all_brands, default=all_brands)
    filtered_df = df[df['Brand'].isin(selected_brands)].copy()
else:
    st.stop()

if filtered_df.empty:
    st.warning("当前筛选无数据。")
    st.stop()

# ==========================================
# 核心修复区：严格匹配 x_range 与绘图坐标
# ==========================================

# 1. 强制生成一个绝对干净的纯字符串列，用于 X 轴。
# 去除可能因为 pandas 自动转换而产生的 ".0" 尾缀（例如 10000.0 变成 10000）
filtered_df['x_axis_str'] = filtered_df['Capacity/mAh'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

# 2. 提取数字以便进行从小到大的逻辑排序
def extract_num(s):
    nums = re.findall(r'\d+', str(s))
    return int(nums[0]) if nums else 0

filtered_df['cap_order'] = filtered_df['x_axis_str'].apply(extract_num)
filtered_df = filtered_df.sort_values('cap_order')

# 3. 提取排序后唯一的纯文本列表，作为 Bokeh 的 x_range
# 这里生成的 unique_x_labels 里面的元素，和下面 source 里的 'x_axis_str' 绝对一模一样
unique_x_labels = filtered_df['x_axis_str'].unique().tolist()

# 生成供 Bokeh 调用的数据源
source = ColumnDataSource(filtered_df)

# ==========================================

# 颜色映射
brands_list = filtered_df['Brand'].unique().tolist()
color_palette = (Category20[20] * 2)[:len(brands_list)] if brands_list else []
color_map = factor_cmap('Brand', palette=color_palette, factors=brands_list)

# 创建图表，严格传入唯一的 x_range 列表
p = figure(
    x_range=unique_x_labels, 
    height=650, 
    sizing_mode="stretch_width",
    title="💡 提示：鼠标悬停在点上查看产品大图",
    toolbar_location="right",
    tools="pan,wheel_zoom,box_zoom,reset"
)

# 绘制散点，x 坐标严格使用我们刚刚生成的 'x_axis_str' 列
scatter = p.circle(
    x='x_axis_str', 
    y='Price', 
    size=18, 
    source=source,
    color=color_map, 
    legend_field='Brand', 
    fill_alpha=0.7, 
    line_color="white"
)

hover = HoverTool(renderers=[scatter])
hover.tooltips = """
<div style="width: 260px; background: white; padding: 12px; border: 1px solid #ddd; border-radius: 8px;">
    <div style="text-align:center; margin-bottom: 8px;">
        <img src="@{URL of Image}" style="max-width: 180px; max-height: 180px; border-radius: 5px;">
    </div>
    <div style="font-size: 14px; font-weight: bold; color: #1f77b4; text-align: center;">@{Brand}</div>
    <div style="font-size: 12px; text-align: center; color: #666; margin-bottom: 8px;">@{Model Number}</div>
    <div style="font-size: 12px; border-top: 1px solid #eee; padding-top: 8px;">
        <b>💰 Price:</b> <span style="color: #d62728; font-weight: bold;">$@{Price}</span><br>
        <b>🔋 Capacity:</b> @{Capacity/mAh}<br>
        <b>🔌 Connect:</b> @{Connect Type}<br>
        <b>⚡ Fast Charge:</b> @{Fast charging}<br>
        <b>📶 Wireless:</b> @{Wireless}<br>
        <b>⭐ Rating:</b> @{Rating} (@{Number of Reviews})<br>
        <b>📦 Size/Weight:</b> @{Size} / @{Weight}<br>
        <b>🏢 Sold by:</b> @{Sold by}<br>
    </div>
</div>
"""
p.add_tools(hover)

p.xaxis.axis_label = "Capacity (mAh)"
p.yaxis.axis_label = "Price (USD)"
p.legend.title = "Brands (Click to hide)"
p.legend.label_text_font_size = "9pt"
p.legend.click_policy = "hide"

st.bokeh_chart(p, use_container_width=True)
